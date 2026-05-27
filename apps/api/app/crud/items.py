from sqlalchemy.ext.asyncio import AsyncSession


async def get_items(db: AsyncSession, user_id: str) -> list:
    raise NotImplementedError
