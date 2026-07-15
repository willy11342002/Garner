"""LangGraph ingest pipeline for POST /items/ — replaces the old
app/core/pipeline.py stage()-decorator + app/workers/process_item.py DAG for
the item-creation flow.

Two properties this buys over the old hand-rolled version:
- Per-node retry via LangGraph's own `RetryPolicy` (was: a manual for-loop).
- Crash/restart recovery via LangGraph's official Postgres checkpointer
  (`app.core.checkpointer`) — if the API process dies mid-run, calling
  `run_ingest()` again for the same item resumes from the last completed
  node instead of losing all progress or restarting from scratch.

Unlike the old pipeline, a stage that exhausts its retries no longer
soft-deletes the item (see old `_fail()` in process_item.py). It just leaves
`<stage>_status="error"` + `<stage>_error` on the row (still committed by
earlier successful stages) and `updated_at` for the frontend's stalled/failed
badge; the user can retry via POST /items/{id}/resume, which calls back into
`run_ingest()` and resumes from checkpoint.

Note: `app/workers/process_item.py` is intentionally left untouched — the
`/items/{id}/reanalyze` and article-reanalyze flows still use it. Migrating
those is out of scope here.
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import TypedDict
from uuid import UUID

from langgraph.graph import END, START, StateGraph
from langgraph.types import RetryPolicy
from sqlalchemy import select

from app.core import events
from app.core.database import AsyncSessionLocal
from app.models.item_tag import TagSource
from app.models.user_item import UserItem

logger = logging.getLogger(__name__)


class IngestState(TypedDict):
    user_item_id: str
    user_id: str
    url: str
    max_video_sec: int
    raw_content: str | None
    analysis: dict | None
    chunk_texts: list[str]
    chunk_embeddings: list[list[float]] | None


# ── Status-tracking wrapper (replaces core/pipeline.py's stage() decorator) ──

def _tracked(name: str, fn):
    """Wrap a node's core logic: touch <name>_status/_error + updated_at on
    entry, success, and (after RetryPolicy exhausts its attempts) failure.
    Runs again from the top on every LangGraph retry attempt, same as the old
    decorator did.
    """

    async def wrapped(state: IngestState) -> dict:
        item_id = UUID(state["user_item_id"])

        async with AsyncSessionLocal() as db:
            item = await db.get(UserItem, item_id)
            if item is None:
                return {}
            setattr(item, f"{name}_status", "running")
            setattr(item, f"{name}_error", None)
            item.updated_at = datetime.now(timezone.utc)
            await db.commit()
        events.emit(state["user_item_id"], name)

        try:
            result = await fn(state)
        except Exception as exc:
            async with AsyncSessionLocal() as db:
                item = await db.get(UserItem, item_id)
                if item is not None:
                    setattr(item, f"{name}_status", "error")
                    setattr(item, f"{name}_error", str(exc)[:2000])
                    item.updated_at = datetime.now(timezone.utc)
                    await db.commit()
            raise

        async with AsyncSessionLocal() as db:
            item = await db.get(UserItem, item_id)
            if item is not None:
                setattr(item, f"{name}_status", "complete")
                item.updated_at = datetime.now(timezone.utc)
                await db.commit()
        return result or {}

    return wrapped


def _retry(max_attempts: int) -> RetryPolicy:
    # Old pipeline retried unconditionally regardless of exception type;
    # LangGraph's default classifier skips ValueError/RuntimeError/etc, which
    # is exactly what these stages raise on bad content — override it.
    return RetryPolicy(max_attempts=max_attempts, initial_interval=2.0, retry_on=lambda exc: True)


# ── Node core logic (ported from process_item.py's _stage_* functions) ──────

async def _fetch_core(state: IngestState) -> dict:
    from app.providers import get_provider

    item_id = UUID(state["user_item_id"])
    url = state["url"]

    async with AsyncSessionLocal() as db:
        user_item = await db.get(UserItem, item_id)
        if user_item is None:
            return {"raw_content": None}

        # Article: the synchronous quick-metadata step (item_service.quick_meta)
        # already ran the one Apify call and got the full text — no-op here.
        if user_item.source_type == "article" and user_item.raw_data and "_quick_raw_content" in user_item.raw_data:
            return {"raw_content": user_item.raw_data["_quick_raw_content"]}

        provider = get_provider(url)

        # YouTube / TikTok / IG / Facebook: quick_meta only ever gave us a
        # title + thumbnail (oEmbed or an og:tag scrape, neither has raw
        # content or a media URL) — the full Apify fetch still needs to run
        # here regardless of provider.
        info = await provider.fetch_info(url, str(user_item.id), content_md=user_item.notes_md)
        if info.title and not user_item.title:
            user_item.title = info.title
        if info.thumbnail_url and not user_item.thumbnail_url:
            user_item.thumbnail_url = info.thumbnail_url
        if info.duration_sec is not None:
            user_item.duration_sec = info.duration_sec
        if info.raw_data:
            user_item.raw_data = info.raw_data
        await db.commit()

        if info.raw_content is not None:
            return {"raw_content": info.raw_content}

    raw_content = await provider.fetch_content(url, info)
    return {"raw_content": raw_content}


async def _assets_core(state: IngestState) -> dict:
    raw_content = state.get("raw_content")
    if not raw_content or not raw_content.strip():
        raise ValueError("No content extracted")

    await _notify_saved(state)
    return {"raw_content": raw_content}


async def _notify_saved(state: IngestState) -> None:
    """Send 'saved' notification right after raw content is confirmed valid —
    title is already readable at this point, AI analysis still running."""
    from app.crud import notifications as crud_notifications
    from app.models.notification import NotificationType

    try:
        async with AsyncSessionLocal() as db:
            item = await db.get(UserItem, UUID(state["user_item_id"]))
            if item is None:
                return
            await crud_notifications.create(
                db,
                user_id=UUID(state["user_id"]),
                type=NotificationType.item_processed,
                title=item.title or state["url"],
                body="已儲存，AI 分析中...",
                item_id=item.id,
            )
            await db.commit()
    except Exception:
        logger.warning("saved-notification failed for item %s", state["user_item_id"], exc_info=True)


async def _note_core(state: IngestState) -> dict:
    from app.crud import tags as crud_tags
    from app.services import ai_service

    user_item_id = UUID(state["user_item_id"])
    user_id = UUID(state["user_id"])
    raw_content = state["raw_content"] or ""
    chunk_texts = ai_service.chunk_text(raw_content)

    async with AsyncSessionLocal() as db:
        candidate_tags = await crud_tags.get_top_tags(db, user_id, limit=50)

    async def _chunk_embed():
        try:
            return await ai_service.embed_many(chunk_texts) if chunk_texts else []
        except Exception:
            return None  # embedding node will recompute

    analysis, chunk_embeddings = await asyncio.gather(
        ai_service.analyze_content(raw_content, candidate_tags=[t.name for t in candidate_tags]),
        _chunk_embed(),
    )

    summary_md = analysis.get("summary_md", {}).get("zh-TW", "")
    if not summary_md:
        raise ValueError("AI returned empty summary")

    async with AsyncSessionLocal() as db:
        user_item = await db.get(UserItem, user_item_id)
        if user_item is None:
            return {"analysis": analysis, "chunk_texts": chunk_texts, "chunk_embeddings": chunk_embeddings}

        title = await ai_service.generate_title(summary_md, raw_title=user_item.title or None)

        user_item.title = title
        user_item.notes_md = summary_md
        user_item.parsed_at = datetime.now(timezone.utc)
        user_item.extract = {
            "raw_content": raw_content,
            "embed_text": analysis.get("embed_text") or summary_md[:500],
            "locations": analysis.get("locations", []),
            "tags": analysis.get("tags", {"zh-TW": [], "en": []}),
        }
        await db.commit()

        try:
            tags_i18n = analysis.get("tags", {})
            zh_tags = tags_i18n.get("zh-TW", [])
            en_tags = tags_i18n.get("en", [])
            for zh_name, en_name in zip(zh_tags, en_tags):
                tag = await crud_tags.get_or_create(
                    db, user_id, name=zh_name, name_i18n={"zh-TW": zh_name, "en": en_name},
                )
                await crud_tags.attach_tag(db, user_item.id, tag.id, source=TagSource.ai)
            await db.commit()
        except Exception:
            await db.rollback()
            logger.warning("tag save failed for item %s", user_item.id, exc_info=True)

    return {"analysis": analysis, "chunk_texts": chunk_texts, "chunk_embeddings": chunk_embeddings}


async def _landmarks_core(state: IngestState) -> dict:
    from app.crud import locations as crud_locations
    from app.services import ai_service, geocoding_service

    user_item_id = UUID(state["user_item_id"])
    raw_content = state.get("raw_content") or ""
    ai_locations = await ai_service.extract_locations(raw_content)

    async with AsyncSessionLocal() as db:
        user_item = await db.get(UserItem, user_item_id)
        if user_item is None:
            return {}

        locations_to_save: list[dict] = []
        raw_data = user_item.raw_data or {}
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
            return {}

        created = []
        for loc_data in locations_to_save:
            loc_obj = await crud_locations.create_location(
                db,
                user_item_id=user_item.id,
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

    return {}


async def _embedding_core(state: IngestState) -> dict:
    from app.crud import chunks as crud_chunks
    from app.services import ai_service

    user_item_id = UUID(state["user_item_id"])
    analysis = state.get("analysis") or {}
    chunk_texts = state.get("chunk_texts") or []
    chunk_embeddings = state.get("chunk_embeddings")

    async with AsyncSessionLocal() as db:
        user_item = await db.get(UserItem, user_item_id)
        if user_item is None:
            return {}

        embed_text = analysis.get("embed_text") or (user_item.notes_md or "")[:500]
        user_item.embedding = await ai_service.embed(embed_text)

        if chunk_embeddings is None:
            chunk_embeddings = await ai_service.embed_many(chunk_texts) if chunk_texts else []
        chunk_records = [
            {"text": chunk, "embedding": emb} for chunk, emb in zip(chunk_texts, chunk_embeddings)
        ]
        await crud_chunks.replace_chunks(db, user_item_id, chunk_records)
        await db.commit()

    return {}


# ── Graph assembly ────────────────────────────────────────────────────────

_graph = None


def _build_graph():
    from app.core.checkpointer import get_checkpointer

    builder = StateGraph(IngestState)
    builder.add_node("fetch", _tracked("fetch", _fetch_core), retry_policy=_retry(3))
    builder.add_node("assets", _tracked("assets", _assets_core), retry_policy=_retry(2))
    builder.add_node("note", _tracked("note", _note_core), retry_policy=_retry(3))
    builder.add_node("landmarks", _tracked("landmarks", _landmarks_core), retry_policy=_retry(2))
    builder.add_node("embedding", _tracked("embedding", _embedding_core), retry_policy=_retry(3))

    builder.add_edge(START, "fetch")
    builder.add_edge("fetch", "assets")
    builder.add_edge("assets", "note")
    builder.add_edge("assets", "landmarks")
    builder.add_edge("note", "embedding")
    builder.add_edge("embedding", END)
    builder.add_edge("landmarks", END)

    return builder.compile(checkpointer=get_checkpointer())


def _get_graph():
    global _graph
    if _graph is None:
        _graph = _build_graph()
    return _graph


# ── Entry point ───────────────────────────────────────────────────────────

async def _item_exists(user_item_id: UUID) -> bool:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(UserItem.id).where(UserItem.id == user_item_id))
        return result.scalar_one_or_none() is not None


async def run_ingest(
    user_id: UUID, user_item_id: UUID, url: str, max_video_sec: int = 1200
) -> None:
    """Run (or resume) the ingest graph for one item.

    Safe to call again for an item whose previous run crashed mid-way or
    whose last stage failed — LangGraph's checkpointer resumes from the last
    completed node instead of restarting from scratch. Used by: item
    creation (background task), same-URL resubmission, and the manual
    POST /items/{id}/resume endpoint.
    """
    if not await _item_exists(user_item_id):
        events.notify(str(user_item_id))
        return

    graph = _get_graph()
    cfg = {"configurable": {"thread_id": str(user_item_id)}}

    existing = await graph.checkpointer.aget_tuple(cfg)
    initial_state: IngestState = {
        "user_item_id": str(user_item_id),
        "user_id": str(user_id),
        "url": url,
        "max_video_sec": max_video_sec,
        "raw_content": None,
        "analysis": None,
        "chunk_texts": [],
        "chunk_embeddings": None,
    }

    try:
        if existing is None:
            await graph.ainvoke(initial_state, config=cfg)
        else:
            # Resume: LangGraph continues from the last completed superstep,
            # re-running only the node(s) that hadn't finished.
            await graph.ainvoke(None, config=cfg)
    except Exception:
        logger.exception("ingest graph failed: user_item_id=%s", user_item_id)
        events.fail(str(user_item_id))
        return

    events.notify(str(user_item_id))
