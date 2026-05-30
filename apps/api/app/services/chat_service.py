"""
chat_service：AI Chat 對話式 RAG 服務。

流程：
  用戶訊息 → RAG 搜尋 → streaming 回覆 → 儲存訊息
  每 10 則訊息 → background task 壓縮 memory_summary
"""

import asyncio
import json
from uuid import UUID

from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import chat as crud_chat
from app.models.chat import MessageRole
from app.schemas.chat import ChatSource
from app.services import ai_service
from app.services.explore_service import rag_retrieve


async def get_sources_for_session(
    db: AsyncSession,
    session_id: UUID,
    user_id: UUID,
    query: str,
) -> tuple[list[dict], list[ChatSource]]:
    """RAG 搜尋，回傳 (llm_items, source_cards)。"""
    hits = await rag_retrieve(db, user_id, query, limit=5)
    llm_items = [
        {"title": ui.content.title, "summary": ui.content.summary}
        for ui, _ in hits
    ]
    sources = [
        ChatSource(
            id=ui.id,
            url=ui.content.url,
            title=ui.content.title,
            thumbnail_url=ui.content.thumbnail_url,
            source_type=ui.content.source_type.value if ui.content.source_type else None,
        )
        for ui, _ in hits
    ]
    return llm_items, sources


async def stream_reply(
    db: AsyncSession,
    session_id: UUID,
    user_id: UUID,
    user_content: str,
    background_tasks: BackgroundTasks,
):
    """
    Agentic SSE stream：
      thinking → tool_call → tool_result → sources → delta* → done
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

    # ── Step 1：分析問題、決定搜尋策略 ───────────────────────────────────
    try:
        analysis = await ai_service.analyze_query(user_content, history)
        reasoning = analysis.get("reasoning", "分析問題中...")
        search_query = analysis.get("search_query", user_content)
    except Exception:
        reasoning = "分析問題中..."
        search_query = user_content

    yield _sse("thinking", {"text": reasoning})

    # ── Step 2：呼叫 search_knowledge_base 工具 ──────────────────────────
    yield _sse("tool_call", {"name": "search_knowledge_base", "query": search_query})

    llm_items, sources = await get_sources_for_session(db, session_id, user_id, search_query)
    cited_ids = [s.id for s in sources]

    yield _sse("tool_result", {
        "count": len(sources),
        "titles": [s.title or s.url for s in sources[:3]],
    })

    yield _sse("sources", [s.model_dump(mode="json") for s in sources])

    # 儲存用戶訊息
    await crud_chat.add_message(db, session_id, MessageRole.user, user_content)

    # ── Step 3：Streaming 回覆 ────────────────────────────────────────────
    full_reply = []
    async for chunk in ai_service.chat_stream(user_content, history, llm_items, memory_summary):
        full_reply.append(chunk)
        yield _sse("delta", {"text": chunk})

    reply_text = "".join(full_reply)

    await crud_chat.add_message(db, session_id, MessageRole.assistant, reply_text, cited_ids or None)
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
