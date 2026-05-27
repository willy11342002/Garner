from sqlalchemy.ext.asyncio import AsyncSession


async def create_item(db: AsyncSession, user_id: str, url: str) -> dict:
    raise NotImplementedError
