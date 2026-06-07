import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import events
from app.crud import chunks as crud_chunks
from app.crud import notifications as crud_notifications
from app.crud import tags as crud_tags
from app.models.content_object import ContentObject
from app.models.item_tag import TagSource
from app.models.notification import NotificationType
from app.providers import get_provider
from app.providers.base import FetchInfo
from app.services import ai_service

logger = logging.getLogger(__name__)


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

    provider = get_provider(url)

    # ── Stage: fetching_info ──────────────────────────────────────────────────
    events.emit(str(user_item_id), "fetching_info")
    try:
        info = await provider.fetch_info(
            url,
            str(content_id),
            content_md=content.content_md,
        )
    except Exception:
        logger.exception("fetch_info failed for url=%s", url)
        await _fail(db, user_id, user_item_id, content, url)
        return

    # commit #1: save Apify metadata immediately
    await _save_fetch_info(db, content, info)

    # ArticleProvider sets raw_content directly; skip fetch_content
    if info.raw_content is not None:
        raw_content: str | None = info.raw_content
    else:
        # ── Stage: fetching_content → understanding ───────────────────────────
        try:
            raw_content = await provider.fetch_content(
                url,
                info,
                stage_cb=lambda stage: events.emit(str(user_item_id), stage),
            )
        except Exception:
            logger.exception("fetch_content failed for url=%s", url)
            await _fail(db, user_id, user_item_id, content, url)
            return

    if not raw_content or not raw_content.strip():
        logger.warning("No content extracted for url=%s", url)
        await _fail(db, user_id, user_item_id, content, url)
        return

    # ── Stage: analyzing ─────────────────────────────────────────────────────
    events.emit(str(user_item_id), "analyzing")
    candidate_tags = await crud_tags.get_top_tags(db, user_id, limit=50)
    analysis = await ai_service.analyze_content(raw_content, candidate_tags=[t.name for t in candidate_tags])

    summary_md = analysis.get("summary_md", {}).get("zh-TW", "")
    if not summary_md:
        logger.error("AI returned empty summary for url=%s", url)
        await _fail(db, user_id, user_item_id, content, url)
        return

    # Generate title for IG (and any other provider that doesn't supply one)
    title = content.title or info.title
    if not title:
        title = await ai_service.generate_title(summary_md)

    # ── Stage: embedding ─────────────────────────────────────────────────────
    events.emit(str(user_item_id), "embedding")
    embed_text = analysis.get("embed_text") or summary_md[:500]
    summary_embedding = await ai_service.embed(embed_text)

    chunk_texts = ai_service.chunk_text(raw_content)
    chunk_records: list[dict] = []
    for chunk in chunk_texts:
        emb = await ai_service.embed(chunk)
        chunk_records.append({"text": chunk, "embedding": emb})

    # ── Stage: validating ────────────────────────────────────────────────────
    events.emit(str(user_item_id), "validating")

    missing = []
    if not title:
        missing.append("title")
    if not summary_md:
        missing.append("summary")
    if not summary_embedding:
        missing.append("embedding")
    if not chunk_records:
        missing.append("chunks")

    if missing:
        logger.error("Validation failed for url=%s, missing=%s", url, missing)
        await _fail(db, user_id, user_item_id, content, url)
        return

    # commit #2: all AI results + parsed_at
    await _save_analysis(
        db, content_id, content, user_id, user_item_id, url,
        title, analysis, summary_embedding, chunk_records,
    )


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _load_content(
    db: AsyncSession,
    content_id: UUID,
    user_item_id: UUID,
) -> ContentObject | None:
    result = await db.execute(select(ContentObject).where(ContentObject.id == content_id))
    content = result.scalar_one_or_none()
    if content is None:
        events.notify(str(user_item_id))
    return content


async def _save_fetch_info(
    db: AsyncSession,
    content: ContentObject,
    info: FetchInfo,
) -> None:
    """commit #1: persist Apify metadata right after fetching_info."""
    if info.title and not content.title:
        content.title = info.title
    if info.duration_sec is not None:
        content.duration_sec = info.duration_sec
    if info.thumbnail_url:
        content.thumbnail_url = info.thumbnail_url
    if info.raw_data:
        content.raw_data = info.raw_data
    await db.commit()


async def _save_analysis(
    db: AsyncSession,
    content_id: UUID,
    content: ContentObject,
    user_id: UUID,
    user_item_id: UUID,
    url: str,
    title: str,
    analysis: dict,
    summary_embedding: list[float],
    chunk_records: list[dict],
) -> None:
    """commit #2: AI results, embeddings, chunks, tags, parsed_at."""
    summary_i18n = analysis.get("summary", {})
    summary_md = analysis.get("summary_md", {})
    tags_i18n = analysis.get("tags", {})

    if not content.title:
        content.title = title

    content.summary_i18n = summary_i18n
    content.summary = summary_md.get("zh-TW", "")
    content.embedding = summary_embedding

    await crud_chunks.replace_chunks(db, content_id, chunk_records)

    zh_tags = tags_i18n.get("zh-TW", [])
    en_tags = tags_i18n.get("en", [])
    for zh_name, en_name in zip(zh_tags, en_tags):
        tag = await crud_tags.get_or_create(
            db, user_id, name=zh_name,
            name_i18n={"zh-TW": zh_name, "en": en_name},
        )
        await crud_tags.attach_tag(db, user_item_id, tag.id, source=TagSource.ai)

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


async def _fail(
    db: AsyncSession,
    user_id: UUID,
    user_item_id: UUID,
    content: ContentObject,
    url: str,
) -> None:
    from app.models.user_item import UserItem

    result = await db.execute(select(UserItem).where(UserItem.id == user_item_id))
    user_item = result.scalar_one_or_none()
    if user_item:
        user_item.deleted_at = datetime.now(timezone.utc)

    await crud_notifications.create(
        db,
        user_id=user_id,
        type=NotificationType.item_failed,
        title="內容處理失敗",
        body=f"「{content.title or url}」無法取得或分析內容，請稍後再試。",
        item_id=user_item_id,
    )

    await db.commit()
    events.fail(str(user_item_id))
