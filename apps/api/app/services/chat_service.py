"""
chat_service：AI Chat 對話式 RAG 服務。

流程：
  用戶訊息 → plan_tools → 執行各 tool → merge 結果 → streaming 回覆 → 儲存訊息
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
    from sqlalchemy import select

    cutoff = await _get_search_cutoff(db)
    embedding = await ai_service.embed(query)
    chunk_hits = await crud_chunks.semantic_search(db, user_id, embedding, limit=limit * 2, cutoff=cutoff, offset=offset)

    if chunk_hits:
        seen: dict[UUID, tuple[UserItem, float]] = {}
        for chunk, dist in chunk_hits:
            result = await db.execute(
                select(UserItem)
                .where(
                    UserItem.id == chunk.user_item_id,
                    UserItem.user_id == user_id,
                    UserItem.deleted_at.is_(None),
                )
                .limit(1)
            )
            ui = result.scalar_one_or_none()
            if ui and ui.id not in seen:
                seen[ui.id] = (ui, dist)
            if len(seen) >= limit:
                break
        return list(seen.values())

    return await crud_items.semantic_search(db, user_id, embedding, limit=limit, cutoff=cutoff, saved_after=None, saved_before=None, exclude_ids=None)


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


_TOOL_HANDLERS = {
    "search": _exec_search,
}


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
    Agentic SSE stream：
      thinking → tool_call(s) → tool_result(s) → sources → delta* → done
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
    today = datetime.now(timezone.utc).date().isoformat()

    # ── Step 1：規劃工具 ──────────────────────────────────────────────────────
    try:
        plan = await ai_service.plan_tools(user_content, history, today)
        reasoning = plan.get("reasoning", "分析問題中...")
        tools = plan.get("tools") or []
    except Exception:
        reasoning = "分析問題中..."
        tools = [{"name": "search", "query": user_content}]

    yield _sse("thinking", {"text": reasoning})

    # ── Step 2：執行各 tool ──────────────────────────────────────────────────
    # 不強制補 semantic_search：若 AI 判斷不需要工具（閒聊、對話脈絡問題），直接跳過

    all_items: list[ItemWithDist] = []
    seen_ids: set[UUID] = set()
    process_steps: list[dict] = []
    created_article: dict | None = None  # 本輪建立的文章草稿

    # ── Preload 指定 items（探索頁跳轉時直接注入 context）──────────────────────
    if context_item_ids:
        preloaded = await crud_items.get_by_ids(db, user_id, context_item_ids)
        for ui in preloaded:
            if ui.id not in seen_ids:
                seen_ids.add(ui.id)
                all_items.append((ui, None))

    for tool in tools:
        name = tool.get("name", "")
        tool_payload = {k: v for k, v in tool.items()}
        yield _sse("tool_call", tool_payload)

        # ── create_article 特殊處理 ──────────────────────────────────────────
        if name == "create_article":
            try:
                draft = await create_article_draft(
                    db, user_id,
                    title=tool.get("title", "未命名文章"),
                    content_markdown=tool.get("content", ""),
                    summary=tool.get("summary"),
                )
                created_article = draft
                yield _sse("article_draft", draft)
                tool_result = {"tool": name, "created": True, "article_id": draft["id"], "title": draft["title"]}
                process_steps.append({"toolCall": tool_payload, "toolResult": tool_result, "articleDraft": draft})
            except Exception:
                tool_result = {"tool": name, "created": False}
                process_steps.append({"toolCall": tool_payload, "toolResult": tool_result})
            yield _sse("tool_result", tool_result)
            continue

        # ── 一般 search 工具 ─────────────────────────────────────────────────
        handler = _TOOL_HANDLERS.get(name)
        if not handler:
            continue

        try:
            hits = await handler(db, user_id, tool)
        except Exception:
            hits = []

        new_hits = [(ui, dist) for ui, dist in hits if ui.id not in seen_ids]
        for ui, dist in new_hits:
            seen_ids.add(ui.id)
            all_items.append((ui, dist))

        tool_result = {
            "tool": name,
            "count": len(new_hits),
            "titles": [ui.title or ui.url for ui, _ in new_hits],
        }
        process_steps.append({"toolCall": tool_payload, "toolResult": tool_result})
        yield _sse("tool_result", tool_result)

    # ── Step 2.5：Reflect — 判斷結果是否足夠，不足補搜一輪 ──────────────────────
    # 只在有執行過 search 工具且沒有 create_article 時才 reflect
    executed_searches = [s["toolCall"] for s in process_steps if s["toolCall"].get("name") == "search"]
    if executed_searches and not created_article:
        result_titles = [ui.title or ui.url for ui, _ in all_items]
        try:
            reflect = await ai_service.reflect_results(user_content, executed_searches, result_titles)
        except Exception:
            reflect = {"sufficient": True}

        yield _sse("thinking", {"text": reflect.get("reasoning", "")})

        if not reflect.get("sufficient", True) and reflect.get("follow_up"):
            follow_up = reflect["follow_up"]
            yield _sse("tool_call", follow_up)
            try:
                extra_hits = await _exec_search(db, user_id, follow_up)
            except Exception:
                extra_hits = []

            new_hits = [(ui, dist) for ui, dist in extra_hits if ui.id not in seen_ids]
            for ui, dist in new_hits:
                seen_ids.add(ui.id)
                all_items.append((ui, dist))

            tool_result = {
                "tool": "search",
                "count": len(new_hits),
                "titles": [ui.title or ui.url for ui, _ in new_hits],
            }
            process_steps.append({"toolCall": follow_up, "toolResult": tool_result})
            yield _sse("tool_result", tool_result)

    # 最多取 10 筆
    all_items = all_items[:10]
    sources = [_to_chat_source(ui, dist) for ui, dist in all_items]

    # ── Step 2.7：filter_sources — AI 篩選真正相關的知識筆記 ──────────────────
    cited_sources: list = sources
    if sources and not created_article:
        filter_tool_call = {"name": "filter_sources"}
        yield _sse("tool_call", filter_tool_call)
        try:
            filter_items = [{"title": s.title or s.url} for s in sources]
            relevant_indices = await ai_service.filter_sources(user_content, filter_items)
            cited_sources = [sources[i] for i in relevant_indices]
        except Exception:
            cited_sources = sources
        filter_tool_result = {
            "tool": "filter_sources",
            "count": len(cited_sources),
            "titles": [s.title or s.url or "" for s in cited_sources],
        }
        process_steps.append({"toolCall": filter_tool_call, "toolResult": filter_tool_result})
        yield _sse("tool_result", filter_tool_result)

    cited_ids = [s.id for s in cited_sources]

    yield _sse("sources", [s.model_dump(mode="json") for s in sources])
    yield _sse("cited_sources", [s.model_dump(mode="json") for s in cited_sources])

    # 儲存用戶訊息（若帶有知識節點，一起存入 cited_item_ids 供前端重建顯示）
    await crud_chat.add_message(
        db, session_id, MessageRole.user, user_content,
        cited_item_ids=context_item_ids if context_item_ids else None,
    )

    # ── Step 3：Streaming 回覆 ────────────────────────────────────────────────
    # chunk 搜尋只在 search 工具有找到 items 時才執行
    # retrieved_ids 為空時不做搜尋，避免 item_ids=None 變成全庫搜尋洩漏給 LLM
    cutoff = await _get_search_cutoff(db)
    retrieved_ids = [ui.id for ui, _ in all_items]
    if retrieved_ids:
        query_embedding = await ai_service.embed(user_content)
        chunk_hits = await crud_chunks.semantic_search(
            db, user_id, query_embedding, limit=12, cutoff=cutoff, item_ids=retrieved_ids
        )
    else:
        chunk_hits = []

    # 建立 user_item_id → UserItem 的 mapping
    item_map = {ui.id: ui for ui, _ in all_items}

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

    if chunk_hits:
        llm_items = [
            {
                "title": item_map.get(c.user_item_id, None) and item_map[c.user_item_id].title or "(無標題)",
                "summary": c.text,
                "tags": _item_tags(item_map[c.user_item_id]) if c.user_item_id in item_map else [],
                "locations": _item_locations(item_map[c.user_item_id]) if c.user_item_id in item_map else [],
            }
            for c, _ in chunk_hits
        ]
    else:
        llm_items = [
            {
                "title": ui.title,
                "summary": (ui.notes_md or "")[:800],
                "tags": _item_tags(ui),
                "locations": _item_locations(ui),
            }
            for ui, _ in all_items
        ]

    full_reply = []
    async for chunk in ai_service.chat_stream(
        user_content, history, llm_items, context_summary,
        created_article_title=created_article["title"] if created_article else None,
    ):
        full_reply.append(chunk)
        yield _sse("delta", {"text": chunk})

    reply_text = "".join(full_reply)

    await crud_chat.add_message(
        db, session_id, MessageRole.assistant, reply_text,
        cited_ids or None,
        process_log={"thinking": reasoning, "steps": process_steps},
    )
    await crud_chat.touch_session(db, session_id)

    msg_count = await crud_chat.count_messages(db, session_id)
    if msg_count % 8 == 0:
        # 壓縮對象：8 則以前的所有歷史（不含最新這輪）
        to_compress = history[:-8] if len(history) > 8 else history
        if to_compress:
            background_tasks.add_task(_compress_context, session_id, context_summary, to_compress)

    yield _sse("done", {})


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
