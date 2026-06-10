from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.item_tag import ItemTag
from app.models.notification import Notification
from app.models.subscription import Subscription
from app.models.tag import Tag
from app.models.user import User
from app.models.user_item import UserItem

async def get_by_id(db: AsyncSession, user_id: UUID) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_or_create(db: AsyncSession, user_id: UUID, email: str | None, username: str, avatar_url: str | None = None) -> User:
    user = await get_by_id(db, user_id)
    if user is None:
        user = User(id=user_id, email=email, username=username, avatar_url=avatar_url)
        db.add(user)
        await db.flush()
    return user


async def update_user(
    db: AsyncSession,
    user: User,
    avatar_url: str | None = None,
) -> User:
    if avatar_url is not None:
        user.avatar_url = avatar_url
    await db.flush()
    return user


async def delete_user(db: AsyncSession, user: User) -> None:
    uid = user.id

    # 1. item_tags（被 user_items 和 tags 雙向參考，必須先刪）
    user_item_ids = select(UserItem.id).where(UserItem.user_id == uid)
    await db.execute(delete(ItemTag).where(ItemTag.user_item_id.in_(user_item_ids)))

    # 2. notifications（item_id 外鍵指向 user_items，必須先刪）
    await db.execute(delete(Notification).where(Notification.user_id == uid))

    # 3. user_items
    await db.execute(delete(UserItem).where(UserItem.user_id == uid))

    # 4. tags
    await db.execute(delete(Tag).where(Tag.user_id == uid))

    # 5. subscriptions
    await db.execute(delete(Subscription).where(Subscription.user_id == uid))

    # 6. user（chat_folders / chat_sessions 有 ondelete=CASCADE，DB 自動處理）
    await db.delete(user)
    await db.flush()
