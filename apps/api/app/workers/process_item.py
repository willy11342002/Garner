import logging
from datetime import date, datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import events

logger = logging.getLogger(__name__)
from app.crud import chunks as crud_chunks
from app.crud import tags as crud_tags
from app.models.content_object import ContentObject, SourceType, TranscriptionSource, detect_source_type
from app.models.item_tag import TagSource
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
    transcription_source: TranscriptionSource | None = None

    if source_type == SourceType.youtube:
        from app.services import youtube_service
        raw_content, whisper_seconds, duration_sec, title, transcription_source_str = await youtube_service.fetch_content(
            db, user_id, url
        )
        transcription_source = TranscriptionSource(transcription_source_str) if transcription_source_str else None

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
    if transcription_source is not None:
        content.transcription_source = transcription_source

    if raw_content is not None:
        try:
            analysis = await ai_service.analyze_content(raw_content)
            summary_i18n: dict[str, str] = analysis.get("summary", {})
            content.summary_i18n = summary_i18n
            # Keep summary as zh-TW fallback for backward compatibility
            content.summary = summary_i18n.get("zh-TW") or summary_i18n.get("en", "")
            # Embed the English summary for fallback / explore_service
            embed_text = summary_i18n.get("en") or content.summary
            content.embedding = await ai_service.embed(embed_text)

            # Chunk raw_content and embed each chunk for fine-grained RAG
            chunk_texts = ai_service.chunk_text(raw_content)
            chunk_records: list[dict] = []
            for chunk in chunk_texts:
                emb = await ai_service.embed(chunk)
                chunk_records.append({"text": chunk, "embedding": emb})
            await crud_chunks.replace_chunks(db, content_id, chunk_records)

            # Create and attach AI-generated tags
            tags_i18n: dict[str, list[str]] = analysis.get("tags", {})
            zh_tags = tags_i18n.get("zh-TW", [])
            en_tags = tags_i18n.get("en", [])
            for zh_name, en_name in zip(zh_tags, en_tags):
                tag = await crud_tags.get_or_create(
                    db, user_id, name=zh_name,
                    name_i18n={"zh-TW": zh_name, "en": en_name},
                )
                await crud_tags.attach_tag(db, user_item_id, tag.id, source=TagSource.ai)
        except Exception:
            logger.exception("AI processing failed for content_id=%s user_id=%s", content_id, user_id)

        if whisper_seconds is not None:
            db.add(WhisperUsage(user_id=user_id, date=date.today(), used_seconds=whisper_seconds))

    content.parsed_at = datetime.now(timezone.utc)
    await db.commit()

    events.notify(str(user_item_id))
