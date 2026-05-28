from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.content_object import ContentObject
from app.models.user_item import UserItem, UserItemStatus


async def get_all(db: AsyncSession, user_id: UUID) -> list[UserItem]:
    result = await db.execute(
        select(UserItem)
        .where(
            UserItem.user_id == user_id,
            UserItem.deleted_at.is_(None),
            UserItem.status == UserItemStatus.active,
        )
        .options(joinedload(UserItem.content))
        .order_by(UserItem.saved_at.desc())
    )
    return list(result.scalars().all())


async def get_archived(db: AsyncSession, user_id: UUID) -> list[UserItem]:
    result = await db.execute(
        select(UserItem)
        .where(
            UserItem.user_id == user_id,
            UserItem.deleted_at.is_(None),
            UserItem.status == UserItemStatus.archived,
        )
        .options(joinedload(UserItem.content))
        .order_by(UserItem.saved_at.desc())
    )
    return list(result.scalars().all())


async def get_one(db: AsyncSession, user_id: UUID, item_id: UUID) -> UserItem | None:
    result = await db.execute(
        select(UserItem)
        .where(
            UserItem.id == item_id,
            UserItem.user_id == user_id,
            UserItem.deleted_at.is_(None),
        )
        .options(joinedload(UserItem.content))
    )
    return result.scalar_one_or_none()


async def create(db: AsyncSession, user_id: UUID, content: ContentObject) -> UserItem:
    user_item = UserItem(user_id=user_id, content_id=content.id)
    db.add(user_item)
    await db.flush()
    await db.refresh(user_item)
    return user_item


async def soft_delete(db: AsyncSession, user_item: UserItem) -> UserItem:
    user_item.deleted_at = datetime.now(timezone.utc)
    user_item.status = UserItemStatus.deleted
    await db.flush()
    return user_item
