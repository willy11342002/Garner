import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import events
from app.crud import chunks as crud_chunks
from app.crud import locations as crud_locations
from app.crud import notifications as crud_notifications
from app.crud import tags as crud_tags
from app.models.user_item import UserItem
from app.models.item_tag import TagSource
from app.models.notification import NotificationType
from app.providers import get_provider
from app.providers.base import FetchInfo
from app.services import ai_service
from app.services import geocoding_service

logger = logging.getLogger(__name__)


async def process_item(
    db: AsyncSession,
    user_id: UUID,
    user_item_id: UUID,
    url: str,
    max_video_sec: int = 1200,
) -> None:
    user_item = await _load_item(db, user_item_id)
    if user_item is None:
        return

    provider = get_provider(url)

    # ── Stage: fetching_info ──────────────────────────────────────────────────
    events.emit(str(user_item_id), "fetching_info")
    try:
        info = await provider.fetch_info(
            url,
            str(user_item_id),
            content_md=user_item.notes_md,
        )
    except Exception:
        logger.exception("fetch_info failed for url=%s", url)
        await _fail(db, user_id, user_item_id, user_item, url)
        return

    # commit #1: 立即儲存 provider metadata（title/thumbnail 等）
    await _save_fetch_info(db, user_item, info)

    # ArticleProvider 直接提供 raw_content，跳過 fetch_content
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
            await _fail(db, user_id, user_item_id, user_item, url)
            return

    if not raw_content or not raw_content.strip():
        logger.warning("No content extracted for url=%s", url)
        await _fail(db, user_id, user_item_id, user_item, url)
        return

    # ── Stage: analyzing ─────────────────────────────────────────────────────
    events.emit(str(user_item_id), "analyzing")
    candidate_tags = await crud_tags.get_top_tags(db, user_id, limit=50)
    analysis = await ai_service.analyze_content(
        raw_content, candidate_tags=[t.name for t in candidate_tags]
    )

    summary_md = analysis.get("summary_md", {}).get("zh-TW", "")
    if not summary_md:
        logger.error("AI returned empty summary for url=%s", url)
        await _fail(db, user_id, user_item_id, user_item, url)
        return

    raw_title = user_item.title or info.title
    title = await ai_service.generate_title(summary_md, raw_title=raw_title or None)

    # ── Stage: embedding ─────────────────────────────────────────────────────
    events.emit(str(user_item_id), "embedding")
    embed_text = analysis.get("embed_text") or summary_md[:500]
    summary_embedding = await ai_service.embed(embed_text)

    # Store intermediate AI outputs for future re-runs (avoids re-fetching from provider)
    extract_snapshot = {
        "raw_content": raw_content,
        "embed_text": embed_text,
        "locations": analysis.get("locations", []),
        "tags": analysis.get("tags", {"zh-TW": [], "en": []}),
    }

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
        await _fail(db, user_id, user_item_id, user_item, url)
        return

    # commit #2: AI 結果 + parsed_at
    await _save_analysis(
        db, user_item, user_id, user_item_id, url,
        title, analysis, summary_embedding, chunk_records, extract_snapshot,
    )

    # Stage: locating
    try:
        await _save_locations(db, user_item_id, user_item, extract_snapshot["locations"])
    except Exception:
        logger.exception("Failed to save locations for user_item_id=%s", user_item_id)


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _load_item(db: AsyncSession, user_item_id: UUID) -> UserItem | None:
    result = await db.execute(select(UserItem).where(UserItem.id == user_item_id))
    user_item = result.scalar_one_or_none()
    if user_item is None:
        events.notify(str(user_item_id))
    return user_item


async def _save_fetch_info(
    db: AsyncSession,
    user_item: UserItem,
    info: FetchInfo,
) -> None:
    """commit #1: 儲存 provider 抓到的 metadata。"""
    if info.title and not user_item.title:
        user_item.title = info.title
    if info.thumbnail_url and not user_item.thumbnail_url:
        user_item.thumbnail_url = info.thumbnail_url
    if info.duration_sec is not None:
        user_item.duration_sec = info.duration_sec
    if info.raw_data:
        user_item.raw_data = info.raw_data
    await db.commit()


async def _save_analysis(
    db: AsyncSession,
    user_item: UserItem,
    user_id: UUID,
    user_item_id: UUID,
    url: str,
    title: str,
    analysis: dict,
    summary_embedding: list[float],
    chunk_records: list[dict],
    extract_snapshot: dict,
) -> None:
    """commit #2: AI 結果、embedding、chunks、tags、parsed_at。"""
    notes_md = analysis.get("summary_md", {}).get("zh-TW", "")
    tags_i18n = analysis.get("tags", {})
    now = datetime.now(timezone.utc)

    user_item.title = title
    user_item.notes_md = notes_md
    user_item.embedding = summary_embedding
    user_item.parsed_at = now
    user_item.extract = extract_snapshot

    await crud_chunks.replace_chunks(db, user_item_id, chunk_records)

    zh_tags = tags_i18n.get("zh-TW", [])
    en_tags = tags_i18n.get("en", [])
    for zh_name, en_name in zip(zh_tags, en_tags):
        tag = await crud_tags.get_or_create(
            db, user_id, name=zh_name,
            name_i18n={"zh-TW": zh_name, "en": en_name},
        )
        await crud_tags.attach_tag(db, user_item_id, tag.id, source=TagSource.ai)

    await crud_notifications.create(
        db,
        user_id=user_id,
        type=NotificationType.item_processed,
        title=user_item.title or url,
        item_id=user_item_id,
    )

    await db.commit()
    events.notify(str(user_item_id))


async def _save_locations(
    db: AsyncSession,
    user_item_id: UUID,
    user_item: UserItem,
    ai_locations: list[dict],
) -> None:
    locations_to_save: list[dict] = []

    # Source 1: IG metadata locationName
    raw_data = user_item.raw_data or {}
    metadata_name = raw_data.get("locationName")
    if metadata_name and isinstance(metadata_name, str):
        locations_to_save.append({"name": metadata_name, "order": 0, "source": "metadata"})

    # Source 2: AI-extracted locations
    metadata_names = {s["name"] for s in locations_to_save}
    for loc in ai_locations:
        if not isinstance(loc, dict):
            continue
        name = loc.get("name")
        if name and name not in metadata_names:
            locations_to_save.append({
                "name": name,
                "order": loc.get("order", 0),
                "source": "ai",
            })

    if not locations_to_save:
        return

    created = []
    for loc_data in locations_to_save:
        loc_obj = await crud_locations.create_location(
            db,
            user_item_id=user_item_id,
            name=loc_data["name"],
            source=loc_data["source"],
            order_index=loc_data["order"],
        )
        created.append(loc_obj)

    await db.flush()

    for loc_obj in created:
        lat, lng = await geocoding_service.geocode(loc_obj.name)
        loc_obj.lat = lat
        loc_obj.lng = lng

    await db.commit()


async def _fail(
    db: AsyncSession,
    user_id: UUID,
    user_item_id: UUID,
    user_item: UserItem,
    url: str,
) -> None:
    user_item.deleted_at = datetime.now(timezone.utc)

    await crud_notifications.create(
        db,
        user_id=user_id,
        type=NotificationType.item_failed,
        title="內容處理失敗",
        body=f"「{user_item.title or url}」無法取得或分析內容，請稍後再試。",
        item_id=user_item_id,
    )

    await db.commit()
    events.fail(str(user_item_id))
