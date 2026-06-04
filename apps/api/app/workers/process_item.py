import json
import logging
from datetime import date, datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import events

logger = logging.getLogger(__name__)
from app.crud import chunks as crud_chunks
from app.crud import notifications as crud_notifications
from app.crud import tags as crud_tags
from app.models.notification import NotificationType
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

    if source_type == SourceType.article and raw_content is None and content.content_md:
        raw_content = _extract_text_from_tiptap(content.content_md)

    if raw_content is None:
        raise RuntimeError(f"No processable content for {url}")

    candidate_tags = await crud_tags.get_top_tags(db, user_id, limit=50)
    candidate_names = [t.name for t in candidate_tags]

    analysis = await ai_service.analyze_content(raw_content, candidate_tags=candidate_names)
    summary_i18n: dict = analysis.get("summary", {})
    summary_md: dict[str, str] = analysis.get("summary_md", {})
    tags_i18n: dict[str, list[str]] = analysis.get("tags", {})

    if not summary_i18n or not summary_md.get("zh-TW") or not tags_i18n:
        raise RuntimeError(
            f"AI returned incomplete results for {url}: "
            f"summary_i18n={bool(summary_i18n)}, summary={bool(summary_md.get('zh-TW'))}, tags={bool(tags_i18n)}"
        )

    content.summary_i18n = summary_i18n
    content.summary = summary_md.get("zh-TW", "")
    embed_text = analysis.get("embed_text") or content.summary[:500]
    content.embedding = await ai_service.embed(embed_text)

    chunk_texts = ai_service.chunk_text(raw_content)
    chunk_records: list[dict] = []
    for chunk in chunk_texts:
        emb = await ai_service.embed(chunk)
        chunk_records.append({"text": chunk, "embedding": emb})
    await crud_chunks.replace_chunks(db, content_id, chunk_records)

    zh_tags = tags_i18n.get("zh-TW", [])
    en_tags = tags_i18n.get("en", [])
    for zh_name, en_name in zip(zh_tags, en_tags):
        tag = await crud_tags.get_or_create(
            db, user_id, name=zh_name,
            name_i18n={"zh-TW": zh_name, "en": en_name},
        )
        await crud_tags.attach_tag(db, user_item_id, tag.id, source=TagSource.ai)

    if whisper_seconds is not None:
        db.add(WhisperUsage(user_id=user_id, date=date.today(), used_seconds=whisper_seconds))

    content.parsed_at = datetime.now(timezone.utc)

    title_display = content.title or url
    await crud_notifications.create(
        db,
        user_id=user_id,
        type=NotificationType.item_processed,
        title=title_display,
        item_id=user_item_id,
    )

    await db.commit()

    events.notify(str(user_item_id))


def _extract_text_from_tiptap(content_md: str) -> str | None:
    try:
        doc = json.loads(content_md)
    except Exception:
        return None

    parts: list[str] = []

    def walk(node: dict) -> None:
        if node.get("type") == "text":
            parts.append(node.get("text", ""))
        for child in node.get("content", []):
            walk(child)
        if node.get("type") in ("paragraph", "heading", "blockquote", "listItem"):
            parts.append("\n")

    walk(doc)
    text = "".join(parts).strip()
    return text or None
