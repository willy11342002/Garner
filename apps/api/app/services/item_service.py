from uuid import UUID, uuid4

from fastapi import BackgroundTasks, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.crud import items as crud_items
from app.models.content_object import ContentObject, SourceType, detect_source_type
from app.schemas.item import ItemCreate, ItemRead, ItemSummaryUpdate, ItemUpdate
from app.workers.process_item import process_item


def _item_to_read(user_item, current_user_id: UUID | None = None) -> ItemRead:
    content = user_item.content
    is_owner = (
        current_user_id is not None
        and content.created_by_user_id is not None
        and content.created_by_user_id == current_user_id
    )
    return ItemRead(
        id=user_item.id,
        content_id=content.id,
        url=content.url,
        title=content.title,
        summary=content.summary,
        summary_i18n=content.summary_i18n,
        thumbnail_url=content.thumbnail_url,
        saved_at=user_item.saved_at,
        deleted_at=user_item.deleted_at,
        parsed_at=content.parsed_at,
        status=user_item.status,
        source_type=content.source_type,
        transcription_source=content.transcription_source,
        is_owner=is_owner,
    )


async def _run_process_item(content_id: UUID, user_id: UUID, user_item_id: UUID, url: str) -> None:
    async with AsyncSessionLocal() as db:
        await process_item(db, content_id, user_id, user_item_id, url)


async def create_item(
    db: AsyncSession,
    user_id: UUID,
    data: ItemCreate,
    background_tasks: BackgroundTasks,
) -> ItemRead:
    # In-app note: generate an internal URL and create content owned by this user
    if data.url is None:
        note_url = f"/note/{uuid4()}"
        content = ContentObject(
            url=note_url,
            source_type=SourceType.article,
            title=data.title or "未命名筆記",
            created_by_user_id=user_id,
            summary_i18n={"zh-TW": {"type": "doc", "content": []}},
        )
        db.add(content)
        await db.flush()
        user_item = await crud_items.create(db, user_id, content)
        await db.commit()
        await db.refresh(user_item)
        await db.refresh(user_item.content)
        return _item_to_read(user_item, user_id)

    url = data.url

    result = await db.execute(select(ContentObject).where(ContentObject.url == url))
    content = result.scalar_one_or_none()

    is_new_content = content is None
    if is_new_content:
        content = ContentObject(
            url=url,
            source_type=detect_source_type(url),
            title=data.title,
        )
        db.add(content)
        await db.flush()

    # Check if this user already has a UserItem for this content
    existing = await crud_items.get_by_content_id(db, user_id, content.id, include_deleted=True)
    if existing is not None:
        if existing.deleted_at is not None:
            from datetime import datetime, timezone
            existing.deleted_at = None
            existing.status = "active"
            await db.commit()
            await db.refresh(existing)
            await db.refresh(existing.content)
        return _item_to_read(existing, user_id)

    user_item = await crud_items.create(db, user_id, content)
    await db.commit()
    await db.refresh(user_item)
    await db.refresh(user_item.content)

    if is_new_content or content.parsed_at is None:
        background_tasks.add_task(_run_process_item, content.id, user_id, user_item.id, url)

    return _item_to_read(user_item, user_id)


async def list_items(db: AsyncSession, user_id: UUID) -> list[ItemRead]:
    user_items = await crud_items.get_all(db, user_id)
    return [_item_to_read(ui, user_id) for ui in user_items]


async def get_item(db: AsyncSession, user_id: UUID, item_id: UUID) -> ItemRead:
    user_item = await crud_items.get_one(db, user_id, item_id)
    if user_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return _item_to_read(user_item, user_id)


async def update_item(
    db: AsyncSession, user_id: UUID, item_id: UUID, data: ItemUpdate
) -> ItemRead:
    user_item = await crud_items.get_one(db, user_id, item_id)
    if user_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    if data.title is not None:
        user_item.content.title = data.title
    if data.status is not None:
        user_item.status = data.status
    await db.commit()
    await db.refresh(user_item)
    return _item_to_read(user_item, user_id)


async def update_item_summary(
    db: AsyncSession, user_id: UUID, item_id: UUID, data: ItemSummaryUpdate
) -> ItemRead:
    user_item = await crud_items.get_one(db, user_id, item_id)
    if user_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    content = user_item.content
    if not content.url.startswith("/") or content.created_by_user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot edit summary of external content")

    content.summary_i18n = data.summary_i18n
    await db.commit()
    await db.refresh(user_item)
    return _item_to_read(user_item, user_id)


async def list_archived_items(db: AsyncSession, user_id: UUID) -> list[ItemRead]:
    user_items = await crud_items.get_archived(db, user_id)
    return [_item_to_read(ui, user_id) for ui in user_items]


async def translate_item_notes(
    db: AsyncSession, user_id: UUID, item_id: UUID, locale: str
) -> ItemRead:
    from app.services import ai_service

    user_item = await crud_items.get_one(db, user_id, item_id)
    if user_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    content = user_item.content
    summary_i18n: dict = dict(content.summary_i18n or {})

    if summary_i18n.get(locale):
        return _item_to_read(user_item, user_id)

    zh_md = content.summary
    if not zh_md:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="No source notes to translate")

    translated_md = await ai_service.translate_notes(zh_md)
    summary_i18n[locale] = ai_service.md_to_tiptap(translated_md)
    content.summary_i18n = summary_i18n
    await db.commit()
    await db.refresh(user_item)
    return _item_to_read(user_item, user_id)


async def delete_item(db: AsyncSession, user_id: UUID, item_id: UUID) -> None:
    user_item = await crud_items.get_one(db, user_id, item_id)
    if user_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    await crud_items.soft_delete(db, user_item)
    await db.commit()
