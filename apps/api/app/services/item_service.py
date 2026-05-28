from uuid import UUID

from fastapi import BackgroundTasks, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.crud import items as crud_items
from app.models.content_object import ContentObject, detect_source_type
from app.schemas.item import ItemCreate, ItemRead, ItemUpdate
from app.workers.process_item import process_item


def _item_to_read(user_item) -> ItemRead:
    content = user_item.content
    return ItemRead(
        id=user_item.id,
        url=content.url,
        title=content.title,
        summary=content.summary,
        thumbnail_url=content.thumbnail_url,
        saved_at=user_item.saved_at,
        deleted_at=user_item.deleted_at,
        parsed_at=content.parsed_at,
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
    url = str(data.url)

    result = await db.execute(select(ContentObject).where(ContentObject.url == url))
    content = result.scalar_one_or_none()

    is_new = content is None
    if is_new:
        content = ContentObject(
            url=url,
            source_type=detect_source_type(url),
            title=data.title,
        )
        db.add(content)
        await db.flush()

    user_item = await crud_items.create(db, user_id, content)
    await db.commit()
    await db.refresh(user_item)
    await db.refresh(user_item.content)

    if is_new or content.parsed_at is None:
        background_tasks.add_task(_run_process_item, content.id, user_id, user_item.id, url)

    return _item_to_read(user_item)


async def list_items(db: AsyncSession, user_id: UUID) -> list[ItemRead]:
    user_items = await crud_items.get_all(db, user_id)
    return [_item_to_read(ui) for ui in user_items]


async def get_item(db: AsyncSession, user_id: UUID, item_id: UUID) -> ItemRead:
    user_item = await crud_items.get_one(db, user_id, item_id)
    if user_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return _item_to_read(user_item)


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
    return _item_to_read(user_item)


async def delete_item(db: AsyncSession, user_id: UUID, item_id: UUID) -> None:
    user_item = await crud_items.get_one(db, user_id, item_id)
    if user_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    await crud_items.soft_delete(db, user_item)
    await db.commit()
