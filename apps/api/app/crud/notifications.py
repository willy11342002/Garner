from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification, NotificationType


async def create(
    db: AsyncSession,
    user_id: UUID,
    type: NotificationType,
    title: str,
    body: str | None = None,
    item_id: UUID | None = None,
) -> Notification:
    notification = Notification(user_id=user_id, type=type, title=title, body=body, item_id=item_id)
    db.add(notification)
    await db.flush()
    return notification


async def list_for_user(
    db: AsyncSession,
    user_id: UUID,
    unread_only: bool = False,
    limit: int = 50,
) -> list[Notification]:
    q = select(Notification).where(Notification.user_id == user_id)
    if unread_only:
        q = q.where(Notification.is_read.is_(False))
    q = q.order_by(Notification.created_at.desc()).limit(limit)
    result = await db.execute(q)
    return list(result.scalars().all())


async def mark_read(db: AsyncSession, user_id: UUID, ids: list[UUID]) -> None:
    await db.execute(
        update(Notification)
        .where(Notification.user_id == user_id, Notification.id.in_(ids))
        .values(is_read=True)
    )


async def mark_all_read(db: AsyncSession, user_id: UUID) -> None:
    await db.execute(
        update(Notification)
        .where(Notification.user_id == user_id, Notification.is_read.is_(False))
        .values(is_read=True)
    )
