from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


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
