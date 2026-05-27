from sqlalchemy.ext.asyncio import AsyncSession


async def get_user(db: AsyncSession, user_id: str) -> dict | None:
    raise NotImplementedError
