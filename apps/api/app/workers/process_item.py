from datetime import date, datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import events
from app.models.content_object import ContentObject, SourceType, detect_source_type
from app.models.whisper_usage import WhisperUsage
from app.services import ai_service, thumbnail_service


async def process_item(
    db: AsyncSession,
    content_id: UUID,
    user_id: UUID,
    user_item_id: UUID,
    url: str,
) -> None:
    source_type = detect_source_type(url)

    raw_content: str | None = None
    whisper_seconds: int | None = None
    duration_sec: int | None = None
    title: str | None = None

    if source_type == SourceType.youtube:
        from app.services import youtube_service
        raw_content, whisper_seconds, duration_sec, title = await youtube_service.fetch_content(
            db, user_id, url
        )

    # Thumbnail is always fetched regardless of whether AI content is available
    thumbnail_url = await thumbnail_service.fetch_and_cache_thumbnail(str(content_id), url)

    result = await db.execute(select(ContentObject).where(ContentObject.id == content_id))
    content = result.scalar_one_or_none()
    if content is None:
        events.notify(str(user_item_id))
        return

    if thumbnail_url:
        content.thumbnail_url = thumbnail_url
    if title and not content.title:
        content.title = title
    if duration_sec is not None:
        content.duration_sec = duration_sec

    if raw_content is not None:
        content.summary = await ai_service.summarize(raw_content)
        content.embedding = await ai_service.embed(content.summary)

        if whisper_seconds is not None:
            db.add(WhisperUsage(user_id=user_id, date=date.today(), used_seconds=whisper_seconds))

    # Always mark as processed so SSE knows we're done
    content.parsed_at = datetime.now(timezone.utc)
    await db.commit()

    events.notify(str(user_item_id))
