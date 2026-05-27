from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content_object import ContentObject
from app.services import ai_service, thumbnail_service


async def process_item(db: AsyncSession, content_id: UUID, url: str, raw_content: str) -> None:
    summary = await ai_service.summarize(raw_content)
    embedding = await ai_service.embed(summary)
    thumbnail_url = await thumbnail_service.fetch_and_cache_thumbnail(str(content_id), url)

    result = await db.execute(select(ContentObject).where(ContentObject.id == content_id))
    content = result.scalar_one_or_none()
    if content is None:
        return

    content.summary = summary
    content.embedding = embedding
    content.thumbnail_url = thumbnail_url
    content.parsed_at = datetime.now(timezone.utc)
    await db.commit()
