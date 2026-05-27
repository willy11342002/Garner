from sqlalchemy.ext.asyncio import AsyncSession


async def semantic_search(db: AsyncSession, user_id: str, query: str) -> list:
    raise NotImplementedError
