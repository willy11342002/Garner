"""
chat_service：AI Chat 對話式 RAG 服務。

流程：
  用戶訊息 → plan_tools → 執行各 tool → merge 結果 → streaming 回覆 → 儲存訊息
  每 10 則訊息 → background task 壓縮 memory_summary
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
from app.services.explore_service import rag_retrieve
from app.services.item_service import create_article_draft


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


async def _exec_semantic_search(
    db: AsyncSession, user_id: UUID, tool: dict
) -> list[ItemWithDist]:
    query = tool.get("query", "")
    if not query:
        return []
    hits = await rag_retrieve(db, user_id, query, limit=6)
    return hits  # already list[tuple[UserItem, float]]


async def _exec_structured_filter(
    db: AsyncSession, user_id: UUID, tool: dict
) -> list[ItemWithDist]:
    tags = tool.get("tags") or None
    source_type = tool.get("source_type") or None
    saved_after = _parse_date(tool.get("start_date"))
    saved_before = _parse_date(tool.get("end_date"))

    if not any([tags, source_type, saved_after, saved_before]):
        return []

    items = await crud_items.structured_filter(
        db, user_id,
        tags=tags,
        source_type=source_type,
        saved_after=saved_after,
        saved_before=saved_before,
        limit=8,
    )
    return [(ui, None) for ui in items]


_TOOL_HANDLERS = {
    "semantic_search": _exec_semantic_search,
    "structured_filter": _exec_structured_filter,
}


def _to_chat_source(ui: UserItem, distance: float | None = None) -> ChatSource:
    return ChatSource(
        id=ui.id,
        url=ui.url or ui.content.url,
        title=ui.title,
        thumbnail_url=ui.thumbnail_url,
        source_type=ui.content.source_type.value if ui.content.source_type else None,
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
    memory_summary = await crud_chat.get_memory_summary(db, user_id)
    today = datetime.now(timezone.utc).date().isoformat()

    # ── Step 1：規劃工具 ──────────────────────────────────────────────────────
    try:
        plan = await ai_service.plan_tools(user_content, history, today)
        reasoning = plan.get("reasoning", "分析問題中...")
        tools = plan.get("tools") or []
    except Exception:
        reasoning = "分析問題中..."
        tools = [{"name": "semantic_search", "query": user_content}]

    yield _sse("thinking", {"text": reasoning})

    # ── Step 2：執行各 tool ──────────────────────────────────────────────────
    if not tools:
        tools = [{"name": "semantic_search", "query": user_content}]

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
            "titles": [ui.title or ui.url or ui.content.url for ui, _ in new_hits[:3]],
        }
        process_steps.append({"toolCall": tool_payload, "toolResult": tool_result})
        yield _sse("tool_result", tool_result)

    # 最多取 10 筆
    all_items = all_items[:10]
    sources = [_to_chat_source(ui, dist) for ui, dist in all_items]
    cited_ids = [s.id for s in sources]

    yield _sse("sources", [s.model_dump(mode="json") for s in sources])

    # 儲存用戶訊息（若帶有知識節點，一起存入 cited_item_ids 供前端重建顯示）
    await crud_chat.add_message(
        db, session_id, MessageRole.user, user_content,
        cited_item_ids=context_item_ids if context_item_ids else None,
    )

    # ── Step 3：Streaming 回覆 ────────────────────────────────────────────────
    # 用 chunk 原文取代 summary，讓 AI 能回答細節問題
    query_embedding = await ai_service.embed(user_content)
    chunk_hits = await crud_chunks.semantic_search(db, user_id, query_embedding, limit=12)

    # 建立 content_id → title 的 mapping
    content_titles = {ui.content.id: ui.title for ui, _ in all_items}

    if chunk_hits:
        llm_items = [
            {
                "title": content_titles.get(c.content_id, "(無標題)"),
                "summary": c.text,
            }
            for c, _ in chunk_hits
        ]
    else:
        llm_items = [
            {"title": ui.title, "summary": ui.summary}
            for ui, _ in all_items
        ]

    full_reply = []
    async for chunk in ai_service.chat_stream(
        user_content, history, llm_items, memory_summary,
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
    if msg_count % 10 == 0:
        recent = history[-10:] + [
            {"role": "user", "content": user_content},
            {"role": "assistant", "content": reply_text},
        ]
        background_tasks.add_task(_compress_memory, user_id, memory_summary, recent)

    yield _sse("done", {})


def _sse(event: str, data) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def _compress_memory(
    user_id: UUID,
    current_summary: str | None,
    recent_messages: list[dict],
) -> None:
    from app.core.database import AsyncSessionLocal
    try:
        new_summary = await ai_service.compress_memory(current_summary, recent_messages)
        async with AsyncSessionLocal() as db:
            await crud_chat.set_memory_summary(db, user_id, new_summary)
    except Exception:
        pass
