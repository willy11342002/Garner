import logging
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)

from fastapi import BackgroundTasks, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.crud import items as crud_items
from app.models.content_object import ContentObject, SourceType, detect_source_type
from app.quota_depends import get_video_max_sec
from app.schemas.item import ArticleUpdate, ItemCreate, ItemRead, ItemSummaryUpdate, ItemUpdate
from app.providers.instagram import normalize_instagram_url
from app.providers.youtube import normalize_youtube_url
from app.workers.process_item import process_item


@dataclass
class _ItemCreateResult:
    item: ItemRead
    needs_processing: bool
    content_id: UUID | None = None
    user_item_id: UUID | None = None
    url: str | None = None
    max_video_sec: int = field(default=1200)


def _item_to_read(
    user_item,
    current_user_id: UUID | None = None,
    tags=None,
    include_content_md: bool = True,
) -> ItemRead:
    content = user_item.content
    is_owner = (
        current_user_id is not None
        and content.created_by_user_id is not None
        and content.created_by_user_id == current_user_id
    )
    from app.schemas.tag import TagRead as _TagRead
    resolved_tags = [_TagRead.model_validate(t) for t in (tags or [])]
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
        content_md=content.content_md if include_content_md else None,
        is_draft=user_item.is_draft,
        is_public=user_item.is_public,
        tags=resolved_tags,
    )


async def _run_process_item(
    content_id: UUID, user_id: UUID, user_item_id: UUID, url: str, max_video_sec: int = 1200
) -> None:
    from app.core import events
    async with AsyncSessionLocal() as db:
        try:
            await process_item(db, content_id, user_id, user_item_id, url, max_video_sec)
        except Exception:
            logger.exception(
                "process_item failed: content_id=%s user_id=%s user_item_id=%s",
                content_id, user_id, user_item_id,
            )
            events.fail(str(user_item_id))


async def prepare_item_create(
    db: AsyncSession,
    user_id: UUID,
    data: ItemCreate,
) -> _ItemCreateResult:
    """Create or restore DB records. Returns item data plus processing params when AI processing is needed."""
    if data.url is None:
        item_id = uuid4()
        article_url = f"/app/item/{item_id}"
        content = ContentObject(
            url=article_url,
            source_type=SourceType.article,
            title=data.title or "未命名文章",
            created_by_user_id=user_id,
        )
        db.add(content)
        await db.flush()
        from app.models.user_item import UserItem as UserItemModel
        user_item = UserItemModel(id=item_id, user_id=user_id, content_id=content.id, is_draft=True)
        db.add(user_item)
        await db.flush()
        await db.commit()
        await db.refresh(user_item)
        await db.refresh(user_item.content)
        return _ItemCreateResult(item=_item_to_read(user_item, user_id), needs_processing=False)

    url = normalize_youtube_url(normalize_instagram_url(data.url))
    max_video_sec = await get_video_max_sec(db, user_id)

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

    existing = await crud_items.get_by_content_id(db, user_id, content.id, include_deleted=True)
    if existing is not None:
        if existing.deleted_at is not None:
            from datetime import datetime, timezone
            existing.deleted_at = None
            existing.status = "active"
            await db.commit()
            await db.refresh(existing)
            await db.refresh(existing.content)
        needs = content.parsed_at is None
        return _ItemCreateResult(
            item=_item_to_read(existing, user_id),
            needs_processing=needs,
            content_id=content.id if needs else None,
            user_item_id=existing.id if needs else None,
            url=url if needs else None,
            max_video_sec=max_video_sec,
        )

    user_item = await crud_items.create(db, user_id, content)
    await db.commit()
    await db.refresh(user_item)
    await db.refresh(user_item.content)

    needs = is_new_content or content.parsed_at is None
    return _ItemCreateResult(
        item=_item_to_read(user_item, user_id),
        needs_processing=needs,
        content_id=content.id if needs else None,
        user_item_id=user_item.id if needs else None,
        url=url if needs else None,
        max_video_sec=max_video_sec,
    )


async def create_item(
    db: AsyncSession,
    user_id: UUID,
    data: ItemCreate,
    background_tasks: BackgroundTasks,
) -> ItemRead:
    result = await prepare_item_create(db, user_id, data)
    if result.needs_processing:
        background_tasks.add_task(
            _run_process_item,
            result.content_id,
            user_id,
            result.user_item_id,
            result.url,
            result.max_video_sec,
        )
    return result.item


async def list_items(db: AsyncSession, user_id: UUID) -> list[ItemRead]:
    user_items = await crud_items.get_all(db, user_id)
    return [
        # get_all() already filters confirmed-only tags via selectinload().and_()
        # and defers embedding + content_md, so pass include_content_md=False
        _item_to_read(ui, user_id, tags=[it.tag for it in ui.item_tags], include_content_md=False)
        for ui in user_items
    ]


async def list_items_page(
    db: AsyncSession,
    user_id: UUID,
    *,
    tag_ids: list[UUID] | None = None,
    tag_logic: str = "and",
    saved_after: datetime | None = None,
    sort: str = "saved_desc",
    page: int = 1,
    page_size: int = 25,
) -> "ItemPage":
    from app.schemas.item import ItemPage as _ItemPage
    offset = (page - 1) * page_size
    user_items, total = await crud_items.get_page(
        db, user_id,
        tag_ids=tag_ids,
        tag_logic=tag_logic,
        saved_after=saved_after,
        sort=sort,
        offset=offset,
        limit=page_size,
    )
    items = [
        _item_to_read(ui, user_id, tags=[it.tag for it in ui.item_tags], include_content_md=False)
        for ui in user_items
    ]
    return _ItemPage(items=items, total=total, page=page, page_size=page_size)


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


async def list_articles(db: AsyncSession, user_id: UUID) -> list[ItemRead]:
    from sqlalchemy.orm import joinedload
    from app.models.user_item import UserItem as UserItemModel
    result = await db.execute(
        select(UserItemModel)
        .join(UserItemModel.content)
        .where(
            UserItemModel.user_id == user_id,
            UserItemModel.deleted_at.is_(None),
            ContentObject.created_by_user_id == user_id,
        )
        .options(joinedload(UserItemModel.content))
        .order_by(UserItemModel.saved_at.desc())
    )
    return [_item_to_read(ui, user_id) for ui in result.scalars().all()]


async def update_article(
    db: AsyncSession, user_id: UUID, item_id: UUID, data: ArticleUpdate
) -> ItemRead:
    user_item = await crud_items.get_one(db, user_id, item_id)
    if user_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    content = user_item.content
    if not content.url.startswith("/app/item/") or content.created_by_user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not an owned article")
    if data.title is not None:
        content.title = data.title
    if data.content_md is not None:
        content.content_md = data.content_md
    if data.is_draft is not None:
        user_item.is_draft = data.is_draft
    if data.is_public is not None:
        user_item.is_public = data.is_public
    await db.commit()
    await db.refresh(user_item)
    return _item_to_read(user_item, user_id)


async def publish_article(
    db: AsyncSession,
    user_id: UUID,
    item_id: UUID,
    background_tasks: BackgroundTasks,
) -> ItemRead:
    user_item = await crud_items.get_one(db, user_id, item_id)
    if user_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    content = user_item.content
    if not content.url.startswith("/app/item/") or content.created_by_user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not an owned article")
    user_item.is_draft = False
    await db.commit()
    await db.refresh(user_item)
    # user-written articles always re-run AI (content changes every save)
    background_tasks.add_task(_run_process_item, content.id, user_id, user_item.id, content.url)
    return _item_to_read(user_item, user_id)


async def upload_article_cover(
    db: AsyncSession,
    user_id: UUID,
    item_id: UUID,
    image_bytes: bytes,
    content_type: str,
) -> ItemRead:
    user_item = await crud_items.get_one(db, user_id, item_id)
    if user_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    content = user_item.content
    if content.created_by_user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not an owned article")
    from app.core.supabase import get_supabase
    from app.core.config import settings
    supabase = await get_supabase()
    ext = "jpg" if "jpeg" in content_type or "jpg" in content_type else "png"
    path = f"thumbnails/{content.id}.{ext}"
    try:
        await supabase.storage.from_(settings.storage_bucket).upload(
            path, image_bytes, {"content-type": content_type, "upsert": "true"}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Storage upload failed: {e}",
        )
    thumbnail_url = await supabase.storage.from_(settings.storage_bucket).get_public_url(path)
    content.thumbnail_url = thumbnail_url
    await db.commit()
    await db.refresh(user_item)
    return _item_to_read(user_item, user_id)


async def delete_article_cover(
    db: AsyncSession,
    user_id: UUID,
    item_id: UUID,
) -> ItemRead:
    user_item = await crud_items.get_one(db, user_id, item_id)
    if user_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    content = user_item.content
    if content.created_by_user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not an owned article")
    if content.thumbnail_url:
        from app.core.supabase import get_supabase
        from app.core.config import settings
        supabase = await get_supabase()
        for ext in ("jpg", "png", "webp"):
            path = f"thumbnails/{content.id}.{ext}"
            try:
                await supabase.storage.from_(settings.storage_bucket).remove([path])
            except Exception:
                pass
        content.thumbnail_url = None
        await db.commit()
        await db.refresh(user_item)
    return _item_to_read(user_item, user_id)
