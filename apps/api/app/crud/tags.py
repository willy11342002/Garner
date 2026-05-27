from sqlalchemy.ext.asyncio import AsyncSession


async def get_tags(db: AsyncSession, user_id: str) -> list:
    raise NotImplementedError
