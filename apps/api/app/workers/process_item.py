import asyncio
import logging
from datetime import datetime, timezone
from uuid import UUID

import sentry_sdk
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import events
from app.core.database import AsyncSessionLocal
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

    raw_content = await provider.fetch_content(url, info)
    return info, raw_content


@stage("assets", retries=1)
async def _stage_assets(ctx: StageContext, raw_content: str | None) -> str:
    """Stage 2: validate that we have usable content."""
    if not raw_content or not raw_content.strip():
        raise ValueError("No content extracted")
    return raw_content


@stage("note", retries=2)
async def _stage_note(ctx: StageContext, raw_content: str, user_id: UUID) -> dict:
    """Stage 3: LLM → notes_md + tags + embed_text + locations.

    Tags are saved here (right after the summary commits) so they appear
    without waiting for the embedding stage. The tag save is guarded so a tag
    failure never aborts this stage and soft-deletes the item.
    """
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

    # ── Save tags (decoupled from embedding) ───────────────────────────────────
    try:
        tags_i18n = analysis.get("tags", {})
        zh_tags = tags_i18n.get("zh-TW", [])
        en_tags = tags_i18n.get("en", [])
        for zh_name, en_name in zip(zh_tags, en_tags):
            tag = await crud_tags.get_or_create(
                ctx.db, user_id, name=zh_name,
                name_i18n={"zh-TW": zh_name, "en": en_name},
            )
            await crud_tags.attach_tag(ctx.db, ctx.user_item.id, tag.id, source=TagSource.ai)
        await ctx.db.commit()
    except Exception:
        await ctx.db.rollback()
        logger.warning("tag save failed for item %s", ctx.user_item.id, exc_info=True)

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
async def _stage_embedding(
    ctx: StageContext,
    analysis: dict,
    chunk_texts: list[str],
    chunk_embeddings: list[list[float]] | None,
) -> None:
    """Stage 5: embed the item main vector + persist chunk vectors + notify.

    `chunk_embeddings` is precomputed in parallel with the note stage (chunk
    text comes from raw_content, which needs no LLM analysis). If it is None
    (the parallel embed failed), this stage recomputes it so the retry path
    still works. Tags are saved in the note stage, not here.
    """
    user_item_id = ctx.user_item.id

    # Item main vector — from the (now zh-TW) embed_text, same language as queries.
    embed_text = analysis.get("embed_text") or (ctx.user_item.notes_md or "")[:500]
    ctx.user_item.embedding = await ai_service.embed(embed_text)

    # Chunk vectors — reuse the precomputed embeddings, else recompute.
    if chunk_embeddings is None:
        chunk_embeddings = await ai_service.embed_many(chunk_texts) if chunk_texts else []
    chunk_records = [
        {"text": chunk, "embedding": emb}
        for chunk, emb in zip(chunk_texts, chunk_embeddings)
    ]
    await crud_chunks.replace_chunks(ctx.db, user_item_id, chunk_records)

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
    if not await _item_exists(db, user_item_id):
        return

    # Each stage now opens its own session (see app.core.pipeline), so stages
    # are invoked with the item id rather than a shared context.

    # Stage 1: fetch metadata + raw_content
    try:
        _info, raw_content = await _stage_fetch(user_item_id, url, max_video_sec)
    except Exception:
        await _fail(db, user_id, user_item_id, url)
        return

    # Stage 2: validate assets / content
    try:
        raw_content = await _stage_assets(user_item_id, raw_content)
    except Exception:
        await _fail(db, user_id, user_item_id, url)
        return

    # The "saved" notification is sent later — after the note stage commits the
    # AI-generated title — so it shows the knowledge title rather than the raw
    # URL. It fires in parallel with the embedding stage (see _note_and_embedding)
    # so it doesn't wait for embedding to finish. The modal shows per-stage
    # progress live via events regardless.

    # note (+chunk embed +main embed) and landmarks run concurrently, each in
    # its own session. They write disjoint columns/tables, so this is safe.
    note_exc: Exception | None = None

    async def _note_branch():
        nonlocal note_exc
        note_exc = await _note_and_embedding(user_item_id, raw_content, user_id, url)

    async def _landmarks_branch():
        # ai_locations come from raw_content directly, so this is independent
        # of the note stage and can run in parallel with it.
        try:
            raw = await ai_service.extract_locations(raw_content)
            await _stage_landmarks(user_item_id, raw)
        except Exception:
            pass  # landmark failure is non-fatal

    await asyncio.gather(_note_branch(), _landmarks_branch())

    if note_exc is not None:
        await _fail(db, user_id, user_item_id, url)


async def _note_and_embedding(
    user_item_id: UUID, raw_content: str, user_id: UUID, url: str
) -> Exception | None:
    """Run the note stage and the embedding stage for an item with known
    raw_content. The chunk embedding (pure network, no DB) is computed in
    parallel with the note LLM call; the embedding stage then persists it.

    Returns the note-stage exception if it failed (so the caller can mark the
    item failed), else None. Embedding failure is swallowed — the item is
    already readable once the note stage commits.
    """
    chunk_texts = ai_service.chunk_text(raw_content)
    note_exc: Exception | None = None

    async def _note():
        nonlocal note_exc
        try:
            return await _stage_note(user_item_id, raw_content, user_id)
        except Exception as exc:
            note_exc = exc
            return None

    async def _chunk_embed():
        # No DB access — safe to run alongside the note stage's own session.
        try:
            return await ai_service.embed_many(chunk_texts) if chunk_texts else []
        except Exception:
            return None  # embedding stage will recompute

    analysis, chunk_embeddings = await asyncio.gather(_note(), _chunk_embed())

    if note_exc is not None:
        return note_exc

    # The note stage has committed the AI-generated title, so the "saved"
    # notification can now show it. Fire the notification in parallel with the
    # embedding stage — it only needs the title (already saved), so it doesn't
    # wait for embedding to finish.
    async def _embed():
        try:
            await _stage_embedding(user_item_id, analysis, chunk_texts, chunk_embeddings)
        except Exception:
            pass  # embedding failure doesn't abort — item is already readable

    await asyncio.gather(_notify_saved(user_id, user_item_id, url), _embed())

    return None


async def _notify_saved(user_id: UUID, user_item_id: UUID, url: str) -> None:
    """Send the "saved" notification using the AI-generated title (set by the
    note stage). Opens its own session so it can run alongside the embedding
    stage. Best-effort — a notification failure never aborts processing."""
    try:
        async with AsyncSessionLocal() as db:
            item = await db.get(UserItem, user_item_id)
            if item is None:
                return
            await crud_notifications.create(
                db,
                user_id=user_id,
                type=NotificationType.item_processed,
                title=item.title or url,
                item_id=user_item_id,
            )
            await db.commit()
    except Exception:
        logger.warning("saved-notification failed for item %s", user_item_id, exc_info=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _item_exists(db: AsyncSession, user_item_id: UUID) -> bool:
    result = await db.execute(select(UserItem.id).where(UserItem.id == user_item_id))
    if result.scalar_one_or_none() is None:
        events.notify(str(user_item_id))
        return False
    return True


async def _fail(
    db: AsyncSession,
    user_id: UUID,
    user_item_id: UUID,
    url: str,
) -> None:
    user_item = await db.get(UserItem, user_item_id)
    if user_item is None:
        events.notify(str(user_item_id))
        return
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
