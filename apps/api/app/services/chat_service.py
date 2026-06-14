"""
chat_service：AI Chat 對話式 RAG 服務。

流程：
  用戶訊息 → agentic_chat_stream（原生 tool calling loop）→ 儲存訊息
  每 8 則訊息 → background task 壓縮 session context_summary
"""

import json
from datetime import datetime, timezone
from uuid import UUID

from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import chat as crud_chat
from app.crud import chunks as crud_chunks
from app.crud import items as crud_items
from app.models.chat import MessageRole
from app.models.user_item import UserItem
from app.schemas.chat import ChatSource
from app.services import ai_service
from app.services.item_service import create_article_draft


async def _get_search_cutoff(db: AsyncSession) -> float:
    from sqlalchemy import select
    from app.models.app_setting import AppSetting
    result = await db.execute(
        select(AppSetting.value).where(AppSetting.key == "chain_distance_cutoff")
    )
    val = result.scalar_one_or_none()
    try:
        return float(val) if val is not None else 0.45
    except (TypeError, ValueError):
        return 0.45


async def rag_retrieve(
    db: AsyncSession,
    user_id: UUID,
    query: str,
    limit: int = 8,
    offset: int = 0,
) -> list[tuple[UserItem, float]]:
    import asyncio
    from sqlalchemy import select

    cutoff = await _get_search_cutoff(db)
    embedding = await ai_service.embed(query)
    fetch_limit = limit * 3

    chunk_coro = crud_chunks.semantic_search(
        db, user_id, embedding, limit=fetch_limit, cutoff=cutoff, offset=offset
    )
    article_coro = crud_items.semantic_search(
        db, user_id, embedding, limit=fetch_limit, cutoff=cutoff,
        saved_after=None, saved_before=None, exclude_ids=None,
    )
    chunk_hits, article_hits = await asyncio.gather(chunk_coro, article_coro)

    merged: dict[UUID, tuple[UserItem, float]] = {}

    for ui, dist in article_hits:
        merged[ui.id] = (ui, dist)

    # chunk 命中：若比整篇更近則更新
    chunk_item_ids = list({c.user_item_id for c, _ in chunk_hits})
    if chunk_item_ids:
        chunk_items = {ui.id: ui for ui in await crud_items.get_by_ids(db, user_id, chunk_item_ids)}
        for chunk, dist in chunk_hits:
            iid = chunk.user_item_id
            if iid not in merged or dist < merged[iid][1]:
                ui = chunk_items.get(iid)
                if ui:
                    merged[iid] = (ui, dist)

    sorted_results = sorted(merged.values(), key=lambda t: t[1])
    return sorted_results[offset: offset + limit]


# ---------------------------------------------------------------------------
# Tool 執行層
# ---------------------------------------------------------------------------


def _parse_date(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


ItemWithDist = tuple[UserItem, float | None]


async def _exec_search(
    db: AsyncSession, user_id: UUID, tool: dict
) -> list[ItemWithDist]:
    query = (tool.get("query") or "").strip()
    source_type = tool.get("source_type") or None
    saved_after = _parse_date(tool.get("start_date"))
    saved_before = _parse_date(tool.get("end_date"))
    limit = min(int(tool.get("limit") or 6), 15)
    offset = max(int(tool.get("offset") or 0), 0)
    has_filters = any([source_type, saved_after, saved_before])

    seen_ids: set[UUID] = set()
    results: list[ItemWithDist] = []

    if query:
        for ui, dist in await rag_retrieve(db, user_id, query, limit=limit, offset=offset):
            if ui.id not in seen_ids:
                seen_ids.add(ui.id)
                results.append((ui, dist))

    if has_filters:
        items = await crud_items.structured_filter(
            db, user_id,
            source_type=source_type,
            saved_after=saved_after,
            saved_before=saved_before,
            limit=limit,
            offset=offset,
        )
        for ui in items:
            if ui.id not in seen_ids:
                seen_ids.add(ui.id)
                results.append((ui, None))

    return results




def _to_chat_source(ui: UserItem, distance: float | None = None) -> ChatSource:
    return ChatSource(
        id=ui.id,
        url=ui.url,
        title=ui.title,
        thumbnail_url=ui.thumbnail_url,
        source_type=ui.source_type,
        distance=round(distance, 4) if distance is not None else None,
    )


# ---------------------------------------------------------------------------
# Stream reply
# ---------------------------------------------------------------------------


async def stream_reply(
    db: AsyncSession,
    session_id: UUID,
    user_id: UUID,
    user_content: str,
    background_tasks: BackgroundTasks,
    context_item_ids: list[UUID] | None = None,
):
    """
    Agentic SSE stream using native LLM tool calling.
    Emits: tool_call | tool_result | sources | delta | done
    """
    session = await crud_chat.get_session_with_messages(db, session_id, user_id)
    if not session:
        yield _sse("error", {"message": "session not found"})
        return

    if not session.title:
        title = user_content[:40] + ("…" if len(user_content) > 40 else "")
        await crud_chat.update_session(db, session_id, user_id, title=title)

    history = [{"role": m.role.value, "content": m.content} for m in session.messages]
    context_summary = session.context_summary

    # ── Preload context items (from explore page jump) ───────────────────────
    seen_ids: set[UUID] = set()
    preloaded_items: list[ItemWithDist] = []
    if context_item_ids:
        for ui in await crud_items.get_by_ids(db, user_id, context_item_ids):
            if ui.id not in seen_ids:
                seen_ids.add(ui.id)
                preloaded_items.append((ui, None))

    cutoff = await _get_search_cutoff(db)

    def _item_tags(ui) -> list[str]:
        try:
            return [it.tag.name for it in (ui.item_tags or []) if it.tag]
        except Exception:
            return []

    def _item_locations(ui) -> list[str]:
        try:
            return [loc.name for loc in sorted(ui.locations or [], key=lambda l: l.order_index)]
        except Exception:
            return []

    async def execute_tool(name: str, args: dict) -> dict:
        if name == "search":
            try:
                hits = await _exec_search(db, user_id, args)
            except Exception:
                hits = []
            new_hits = [(ui, dist) for ui, dist in hits if ui.id not in seen_ids]
            for ui, dist in new_hits:
                seen_ids.add(ui.id)

            items_out = [_to_chat_source(ui, dist).model_dump(mode="json") for ui, dist in new_hits]

            # Fetch chunk-level text for context injection
            item_ids = [ui.id for ui, _ in new_hits]
            chunks_out: list[dict] = []
            if item_ids:
                query_embedding = await ai_service.embed(args.get("query") or user_content)
                chunk_hits = await crud_chunks.semantic_search(
                    db, user_id, query_embedding, limit=12, cutoff=cutoff, item_ids=item_ids
                )
                item_map = {ui.id: ui for ui, _ in new_hits}
                chunks_out = [
                    {
                        "title": item_map[c.user_item_id].title if c.user_item_id in item_map else "(無標題)",
                        "text": c.text,
                        "tags": _item_tags(item_map[c.user_item_id]) if c.user_item_id in item_map else [],
                        "locations": _item_locations(item_map[c.user_item_id]) if c.user_item_id in item_map else [],
                    }
                    for c, _ in chunk_hits
                ]
            return {"items": items_out, "chunks": chunks_out}

        if name == "create_article":
            try:
                draft = await create_article_draft(
                    db, user_id,
                    title=args.get("title", "未命名文章"),
                    content_markdown=args.get("content", ""),
                    summary=args.get("summary"),
                )
                return {"draft": draft, "ok": True}
            except Exception:
                return {"draft": None, "ok": False}

        return {}

    # ── Agentic loop ─────────────────────────────────────────────────────────
    reply_text = ""
    process_steps: list[dict] = []
    cited_ids: list[str] = []

    await crud_chat.add_message(
        db, session_id, MessageRole.user, user_content,
        cited_item_ids=context_item_ids if context_item_ids else None,
    )

    async for event_str in ai_service.agentic_chat_stream(
        user_content, history, context_summary, execute_tool
    ):
        # Intercept __meta__ sentinel, don't forward to client
        if "event: __meta__" in event_str:
            import json as _j
            data = _j.loads(event_str.split("data: ", 1)[1])
            reply_text = data.get("reply", "")
            process_steps = data.get("process_steps", [])
            cited_ids = data.get("cited_ids", [])
            continue
        yield event_str

    await crud_chat.add_message(
        db, session_id, MessageRole.assistant, reply_text,
        [UUID(i) for i in cited_ids] if cited_ids else None,
        process_log={"thinking": "", "steps": process_steps},
    )
    await crud_chat.touch_session(db, session_id)

    msg_count = await crud_chat.count_messages(db, session_id)
    if msg_count % 8 == 0:
        to_compress = history[:-8] if len(history) > 8 else history
        if to_compress:
            background_tasks.add_task(_compress_context, session_id, context_summary, to_compress)


def _sse(event: str, data) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def _compress_context(
    session_id: UUID,
    current_summary: str | None,
    old_messages: list[dict],
) -> None:
    from app.core.database import AsyncSessionLocal
    try:
        new_summary = await ai_service.compress_memory(current_summary, old_messages)
        async with AsyncSessionLocal() as db:
            await crud_chat.set_context_summary(db, session_id, new_summary)
    except Exception:
        pass
