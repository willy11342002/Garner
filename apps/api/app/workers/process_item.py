from sqlalchemy.ext.asyncio import AsyncSession

from app.services import ai_service, thumbnail_service


async def process_item(db: AsyncSession, item_id: str, url: str, raw_content: str) -> None:
    summary = await ai_service.summarize(raw_content)
    embedding = await ai_service.embed(summary)
    # TODO: persist summary + embedding to DB
