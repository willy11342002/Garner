import logging
from datetime import date, datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import events

logger = logging.getLogger(__name__)
from app.core.exceptions import VideoTooLongError
from app.crud import chunks as crud_chunks
from app.crud import notifications as crud_notifications
from app.crud import tags as crud_tags
from app.models.content_object import ContentObject
from app.models.item_tag import TagSource
from app.models.notification import NotificationType
from app.models.whisper_usage import WhisperUsage
from app.providers import get_provider
from app.providers.base import FetchResult
from app.services import ai_service


async def process_item(
    db: AsyncSession,
    content_id: UUID,
    user_id: UUID,
    user_item_id: UUID,
    url: str,
    max_video_sec: int = 1200,
) -> None:
    content = await _load_content(db, content_id, user_item_id)
    if content is None:
        return

    try:
        fetch_result = await _fetch_content(db, user_id, url, content, user_item_id, max_video_sec)
    except VideoTooLongError as exc:
        await _cancel_video_too_long(db, user_id, user_item_id, content, url, exc.duration_sec, max_video_sec)
        return

    analysis    = await _analyze_content(fetch_result.raw_content, db, user_id, user_item_id)

    if not fetch_result.title:
        summary_md = analysis.get("summary_md", {}).get("zh-TW", "")
        if summary_md:
            fetch_result.title = await ai_service.generate_title(summary_md)

    await _embed_and_save(db, content_id, content, user_id, user_item_id, url, fetch_result, analysis)


# ── Stage helpers ─────────────────────────────────────────────────────────────


async def _load_content(
    db: AsyncSession,
    content_id: UUID,
    user_item_id: UUID,
) -> ContentObject | None:
    """Load the ContentObject row; notify and return None if it has been deleted."""
    result = await db.execute(select(ContentObject).where(ContentObject.id == content_id))
    content = result.scalar_one_or_none()
    if content is None:
        events.notify(str(user_item_id))
    return content


async def _fetch_content(
    db: AsyncSession,
    user_id: UUID,
    url: str,
    content: ContentObject,
    user_item_id: UUID,
    max_video_sec: int = 1200,
) -> FetchResult:
    """Stage 1–2: fetch raw text from the source URL via the matching provider.

    YouTube emits two sub-stages:
      • fetching_info    — YouTube Data API (title, duration, thumbnail)
      • fetching_content — yt-dlp subtitles → Groq Whisper fallback

    Other providers (article) skip straight to the AI stages.
    Raises RuntimeError if the source yields no usable text.
    """
    provider = get_provider(url)
    fetch_result = await provider.fetch(
        db, user_id, url, content,
        stage_cb=lambda stage: events.emit(str(user_item_id), stage),
        max_duration_sec=max_video_sec,
    )

    if not fetch_result.raw_content or not fetch_result.raw_content.strip():
        raise RuntimeError(f"No processable content for {url}")

    return fetch_result


async def _analyze_content(
    raw_content: str,
    db: AsyncSession,
    user_id: UUID,
    user_item_id: UUID,
) -> dict:
    """Stage 3: send raw text to Claude via OpenRouter and get back:
      • summary_md  — structured Markdown notes (zh-TW)
      • summary     — same notes converted to Tiptap JSON
      • embed_text  — short English description for semantic search
      • tags        — 3–7 zh-TW / en label pairs

    Candidate tags from the user's existing tag list are passed in so Claude
    reuses known vocabulary instead of creating duplicates.
    Raises RuntimeError if Claude returns an incomplete response.
    """
    events.emit(str(user_item_id), "analyzing")

    candidate_tags = await crud_tags.get_top_tags(db, user_id, limit=50)
    candidate_names = [t.name for t in candidate_tags]

    analysis = await ai_service.analyze_content(raw_content, candidate_tags=candidate_names)

    summary_i18n = analysis.get("summary", {})
    summary_md   = analysis.get("summary_md", {})
    tags_i18n    = analysis.get("tags", {})

    if not summary_i18n or not summary_md.get("zh-TW") or not tags_i18n:
        raise RuntimeError(
            f"AI returned incomplete results: "
            f"summary_i18n={bool(summary_i18n)}, "
            f"summary={bool(summary_md.get('zh-TW'))}, "
            f"tags={bool(tags_i18n)}"
        )

    return analysis


async def _embed_and_save(
    db: AsyncSession,
    content_id: UUID,
    content: ContentObject,
    user_id: UUID,
    user_item_id: UUID,
    url: str,
    fetch_result: FetchResult,
    analysis: dict,
) -> None:
    """Stage 4: generate vector embeddings, write everything to DB, and commit.

    Two kinds of embeddings are created:
      • content.embedding  — single 1536-d vector of the summary (used for item-level search)
      • ContentChunk rows  — 400-token chunks of raw_content, each with its own vector
                             (used for fine-grained RAG retrieval)

    Only after both embeddings succeed do we write metadata + AI results and
    stamp parsed_at, so a failure here leaves the item in a retryable state.
    """
    events.emit(str(user_item_id), "embedding")

    summary_i18n = analysis.get("summary", {})
    summary_md   = analysis.get("summary_md", {})
    tags_i18n    = analysis.get("tags", {})
    embed_text   = analysis.get("embed_text") or summary_md.get("zh-TW", "")[:500]

    # Item-level embedding (summary)
    summary_embedding = await ai_service.embed(embed_text)

    # Chunk-level embeddings (raw content split into ~400-token windows)
    chunk_texts = ai_service.chunk_text(fetch_result.raw_content)
    chunk_records: list[dict] = []
    for chunk in chunk_texts:
        emb = await ai_service.embed(chunk)
        chunk_records.append({"text": chunk, "embedding": emb})

    # ── All I/O succeeded — now write to DB ──────────────────────────────────

    # Metadata from provider (title, thumbnail, duration come from YouTube Data API)
    if fetch_result.thumbnail_url:
        content.thumbnail_url = fetch_result.thumbnail_url
    if fetch_result.title and not content.title:
        content.title = fetch_result.title
    if fetch_result.duration_sec is not None:
        content.duration_sec = fetch_result.duration_sec
    if fetch_result.transcription_source is not None:
        content.transcription_source = fetch_result.transcription_source

    # AI results
    content.summary_i18n = summary_i18n
    content.summary      = summary_md.get("zh-TW", "")
    content.embedding    = summary_embedding

    # Chunks (replace existing to stay in sync with latest content)
    await crud_chunks.replace_chunks(db, content_id, chunk_records)

    # Tags: reuse existing tags where possible, create new ones if needed
    zh_tags = tags_i18n.get("zh-TW", [])
    en_tags = tags_i18n.get("en", [])
    for zh_name, en_name in zip(zh_tags, en_tags):
        tag = await crud_tags.get_or_create(
            db, user_id, name=zh_name,
            name_i18n={"zh-TW": zh_name, "en": en_name},
        )
        await crud_tags.attach_tag(db, user_item_id, tag.id, source=TagSource.ai)

    # Record Whisper usage against the user's daily quota (only when Whisper was used)
    if fetch_result.whisper_seconds is not None:
        db.add(WhisperUsage(user_id=user_id, date=date.today(), used_seconds=fetch_result.whisper_seconds))

    # Mark fully processed — parsed_at is the gate checked everywhere to decide
    # whether an item needs (re-)processing. Set it last so any earlier failure
    # leaves the item retryable.
    content.parsed_at = datetime.now(timezone.utc)

    await crud_notifications.create(
        db,
        user_id=user_id,
        type=NotificationType.item_processed,
        title=content.title or url,
        item_id=user_item_id,
    )

    await db.commit()
    events.notify(str(user_item_id))


async def _cancel_video_too_long(
    db: AsyncSession,
    user_id: UUID,
    user_item_id: UUID,
    content: ContentObject,
    url: str,
    duration_sec: int | None,
    max_video_sec: int = 1200,
) -> None:
    """Soft-delete the UserItem and notify the user when a video is too long or duration is unknown."""
    from app.models.user_item import UserItem

    result = await db.execute(select(UserItem).where(UserItem.id == user_item_id))
    user_item = result.scalar_one_or_none()
    if user_item:
        user_item.deleted_at = datetime.now(timezone.utc)

    item_title = content.title or url
    max_minutes = max_video_sec // 60

    if duration_sec is None:
        notif_title = "無法取得影片時長"
        notif_body = f"「{item_title}」影片時長無法確認，為確保服務穩定已拒絕處理。"
    else:
        minutes = duration_sec // 60
        notif_title = f"影片超過時長限制（{minutes} 分鐘）"
        notif_body = f"「{item_title}」影片長度超過 {max_minutes} 分鐘，目前方案僅支援 {max_minutes} 分鐘以內的影片。"

    await crud_notifications.create(
        db,
        user_id=user_id,
        type=NotificationType.item_failed,
        title=notif_title,
        body=notif_body,
        item_id=user_item_id,
    )

    await db.commit()
    events.fail(str(user_item_id))
