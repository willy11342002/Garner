import asyncio
import logging
from datetime import datetime, timezone
from uuid import UUID

import sentry_sdk
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import events
from app.core.pipeline import StageContext, stage
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


# ── Stage functions ───────────────────────────────────────────────────────────

@stage("fetch", retries=2)
async def _stage_fetch(ctx: StageContext, url: str, max_video_sec: int) -> tuple[FetchInfo, str | None]:
    """Stage 1: call provider to get metadata + raw_content."""
    user_item = ctx.user_item
    provider = get_provider(url)

    events.emit(str(user_item.id), "fetching_info")
    info = await provider.fetch_info(url, str(user_item.id), content_md=user_item.notes_md)

    # Commit provider metadata immediately so title/thumbnail appear fast
    if info.title and not user_item.title:
        user_item.title = info.title
    if info.thumbnail_url and not user_item.thumbnail_url:
        user_item.thumbnail_url = info.thumbnail_url
    if info.duration_sec is not None:
        user_item.duration_sec = info.duration_sec
    if info.raw_data:
        user_item.raw_data = info.raw_data
    await ctx.db.commit()

    if info.raw_content is not None:
        return info, info.raw_content

    events.emit(str(user_item.id), "fetching_content")
    raw_content = await provider.fetch_content(
        url, info,
        stage_cb=lambda s: events.emit(str(user_item.id), s),
    )
    return info, raw_content


@stage("assets", retries=1)
async def _stage_assets(ctx: StageContext, raw_content: str | None) -> str:
    """Stage 2: validate that we have usable content."""
    if not raw_content or not raw_content.strip():
        raise ValueError("No content extracted")
    return raw_content


@stage("note", retries=2)
async def _stage_note(ctx: StageContext, raw_content: str, user_id: UUID) -> dict:
    """Stage 3: LLM → notes_md + tags + embed_text + locations."""
    events.emit(str(ctx.user_item.id), "analyzing")
    candidate_tags = await crud_tags.get_top_tags(ctx.db, user_id, limit=50)
    analysis = await ai_service.analyze_content(
        raw_content, candidate_tags=[t.name for t in candidate_tags]
    )

    summary_md = analysis.get("summary_md", {}).get("zh-TW", "")
    if not summary_md:
        raise ValueError("AI returned empty summary")

    raw_title = ctx.user_item.title
    title = await ai_service.generate_title(summary_md, raw_title=raw_title or None)

    ctx.user_item.title = title
    ctx.user_item.notes_md = summary_md
    ctx.user_item.parsed_at = datetime.now(timezone.utc)
    ctx.user_item.extract = {
        "raw_content": raw_content,
        "embed_text": analysis.get("embed_text") or summary_md[:500],
        "locations": analysis.get("locations", []),
        "tags": analysis.get("tags", {"zh-TW": [], "en": []}),
    }
    await ctx.db.commit()

    return analysis


@stage("landmarks", retries=1)
async def _stage_landmarks(ctx: StageContext, ai_locations: list[dict]) -> None:
    """Stage 4: geocode AI-extracted locations + IG metadata location."""
    locations_to_save: list[dict] = []

    raw_data = ctx.user_item.raw_data or {}
    metadata_name = raw_data.get("locationName")
    if metadata_name and isinstance(metadata_name, str):
        locations_to_save.append({"name": metadata_name, "order": 0, "source": "metadata"})

    metadata_names = {s["name"] for s in locations_to_save}
    for loc in ai_locations:
        if not isinstance(loc, dict):
            continue
        name = loc.get("name")
        if name and name not in metadata_names:
            locations_to_save.append({"name": name, "order": loc.get("order", 0), "source": "ai"})

    if not locations_to_save:
        return

    created = []
    for loc_data in locations_to_save:
        loc_obj = await crud_locations.create_location(
            ctx.db,
            user_item_id=ctx.user_item.id,
            name=loc_data["name"],
            source=loc_data["source"],
            order_index=loc_data["order"],
        )
        created.append(loc_obj)

    await ctx.db.flush()

    for loc_obj in created:
        lat, lng = await geocoding_service.geocode(loc_obj.name)
        loc_obj.lat = lat
        loc_obj.lng = lng

    await ctx.db.commit()


@stage("embedding", retries=2)
async def _stage_embedding(ctx: StageContext, analysis: dict, raw_content: str, user_id: UUID, user_item_id: UUID) -> None:
    """Stage 5: embed summary + chunks, save tags, send notification."""
    events.emit(str(user_item_id), "embedding")

    embed_text = analysis.get("embed_text") or ctx.user_item.notes_md[:500]
    summary_embedding = await ai_service.embed(embed_text)
    ctx.user_item.embedding = summary_embedding

    chunk_texts = ai_service.chunk_text(raw_content)
    chunk_records: list[dict] = []
    for chunk in chunk_texts:
        emb = await ai_service.embed(chunk)
        chunk_records.append({"text": chunk, "embedding": emb})

    await crud_chunks.replace_chunks(ctx.db, user_item_id, chunk_records)

    tags_i18n = analysis.get("tags", {})
    zh_tags = tags_i18n.get("zh-TW", [])
    en_tags = tags_i18n.get("en", [])
    for zh_name, en_name in zip(zh_tags, en_tags):
        tag = await crud_tags.get_or_create(
            ctx.db, user_id, name=zh_name,
            name_i18n={"zh-TW": zh_name, "en": en_name},
        )
        await crud_tags.attach_tag(ctx.db, user_item_id, tag.id, source=TagSource.ai)

    await crud_notifications.create(
        ctx.db,
        user_id=user_id,
        type=NotificationType.item_processed,
        title=ctx.user_item.title or "",
        item_id=user_item_id,
    )

    await ctx.db.commit()
    events.notify(str(user_item_id))


# ── DAG orchestration ─────────────────────────────────────────────────────────

async def process_item(
    db: AsyncSession,
    user_id: UUID,
    user_item_id: UUID,
    url: str,
    max_video_sec: int = 1200,
) -> None:
    with sentry_sdk.start_transaction(op="task", name="process_item"):
        await _run_pipeline(db, user_id, user_item_id, url, max_video_sec)


async def _run_pipeline(
    db: AsyncSession,
    user_id: UUID,
    user_item_id: UUID,
    url: str,
    max_video_sec: int,
) -> None:
    user_item = await _load_item(db, user_item_id)
    if user_item is None:
        return

    ctx = StageContext(db=db, user_item=user_item)

    # Stage 1: fetch metadata + raw_content
    try:
        info, raw_content = await _stage_fetch(ctx, url, max_video_sec)
    except Exception:
        await _fail(db, user_id, user_item_id, user_item, url)
        return

    # Stage 2: validate assets / content
    try:
        raw_content = await _stage_assets(ctx, raw_content)
    except Exception:
        await _fail(db, user_id, user_item_id, user_item, url)
        return

    # Stages 3+4 in parallel; stage 5 depends on stage 3
    note_result: dict | None = None
    note_exc: Exception | None = None

    async def _note_then_embedding():
        nonlocal note_result, note_exc
        try:
            note_result = await _stage_note(ctx, raw_content, user_id)
        except Exception as exc:
            note_exc = exc
            return
        # Stage 5 only runs if stage 3 succeeded
        try:
            await _stage_embedding(ctx, note_result, raw_content, user_id, user_item_id)
        except Exception:
            pass  # embedding failure doesn't abort — item is already readable

    async def _landmarks():
        # ai_locations come from raw_content directly, not from extract,
        # so this can safely run in parallel with _note_then_embedding
        try:
            raw = await ai_service.extract_locations(raw_content)
            await _stage_landmarks(ctx, raw)
        except Exception:
            pass  # landmark failure is non-fatal

    await asyncio.gather(_note_then_embedding(), _landmarks())

    if note_exc is not None:
        await _fail(db, user_id, user_item_id, user_item, url)


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _load_item(db: AsyncSession, user_item_id: UUID) -> UserItem | None:
    result = await db.execute(select(UserItem).where(UserItem.id == user_item_id))
    user_item = result.scalar_one_or_none()
    if user_item is None:
        events.notify(str(user_item_id))
    return user_item


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
