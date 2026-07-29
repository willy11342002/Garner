"""
chat_service：AI Chat 對話式 RAG 服務。

流程：
  用戶訊息 → LangGraph 分層 agentic graph（A 監督者派工給 B/C/D 窗口）→ 儲存訊息
  每 8 則訊息 → background task 壓縮 session context_summary

架構見 app/services/ai_service/graph/：A（supervisor）持有對話歷史、負責路由；
B（knowledge）/C（report）/D（trip）三個窗口各自是獨立多步驟 sub-agent，只看得到
A 給的事件敘述，看不到對話歷史。三個窗口的 domain executor（實際 DB／embedding／
建立 item 等）在這裡（session 層）綁定 db/user_id/background_tasks 後建立，透過
RunnableConfig 注入 graph。
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import BackgroundTasks
from google.genai import types
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ai_service._client import model_turn, tool_results, user_turn

logger = logging.getLogger("garner.chat")

from app.crud import chat as crud_chat
from app.crud import chunks as crud_chunks
from app.crud import items as crud_items
from app.models.chat import MessageRole
from app.models.user_item import UserItem
from app.schemas.chat import ChatSource
from app.schemas.item import ItemCreate
from app.services import ai_service
from app.services import item_service
from app.services import report_service
from app.services import trip_service

# A 派工目標 ↔ 對外工具名稱（給歷史回放用，跟 graph/supervisor.py 的 _DISPATCH_TARGET 對應）
_TARGET_TO_TOOL = {
    "knowledge": "dispatch_knowledge_base",
    "report": "dispatch_report_desk",
    "trip": "dispatch_trip_desk",
}

_SUPERVISOR_MAX_ROUNDS = 8


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
# Tool 執行層（各窗口的 domain executor）
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

    # 直接 by ID 查詢（save_url 剛存入、embedding 尚未就緒時使用）
    raw_ids = tool.get("item_ids") or []
    if raw_ids:
        parsed_ids: list[UUID] = []
        for raw in raw_ids if isinstance(raw_ids, list) else []:
            try:
                parsed_ids.append(UUID(str(raw)))
            except (ValueError, TypeError):
                continue
        if parsed_ids:
            items = await crud_items.get_by_ids(db, user_id, parsed_ids)
            return [(ui, None) for ui in items]

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


def _ui_location_names(ui) -> list[str]:
    """取 UserItem 的地點名稱（依 order_index）；relationship 未載入時安全回 []。"""
    try:
        return [loc.name for loc in sorted(ui.locations or [], key=lambda l: l.order_index)]
    except Exception:
        return []


def _to_chat_source(ui: UserItem, distance: float | None = None) -> ChatSource:
    return ChatSource(
        id=ui.id,
        url=ui.url,
        title=ui.title,
        thumbnail_url=ui.thumbnail_url,
        source_type=ui.source_type,
        distance=round(distance, 4) if distance is not None else None,
        locations=_ui_location_names(ui),
    )


def _build_knowledge_executor(
    db: AsyncSession, user_id: UUID, background_tasks: BackgroundTasks,
    seen_ids: set[UUID], all_sources: list[dict], cutoff: float, user_content: str,
    item_tags, item_locations,
):
    """B（知識庫窗口）的 domain executor：search + save_url。"""

    async def executor(name: str, args: dict) -> dict:
        if name == "search":
            try:
                hits = await _exec_search(db, user_id, args)
            except Exception:
                hits = []
            new_hits = [(ui, dist) for ui, dist in hits if ui.id not in seen_ids]
            for ui, dist in new_hits:
                seen_ids.add(ui.id)

            items_out = [_to_chat_source(ui, dist).model_dump(mode="json") for ui, dist in new_hits]
            all_sources.extend(items_out)

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
                        "item_id": str(c.user_item_id),
                        "title": item_map[c.user_item_id].title if c.user_item_id in item_map else "(無標題)",
                        "text": c.text,
                        "tags": item_tags(item_map[c.user_item_id]) if c.user_item_id in item_map else [],
                        "locations": item_locations(item_map[c.user_item_id]) if c.user_item_id in item_map else [],
                    }
                    for c, _ in chunk_hits
                ]
            return {"items": items_out, "chunks": chunks_out}

        if name == "save_url":
            url = (args.get("url") or "").strip()
            if not url:
                return {"ok": False, "error": "url is required"}
            try:
                from app.quota_depends import _get_plan, _get_limit, _count_monthly_saves
                plan_id, plan_name = await _get_plan(db, user_id)
                limit = await _get_limit(db, plan_id, "saves_monthly")
                if limit is not None:
                    used = await _count_monthly_saves(db, user_id)
                    if used >= limit:
                        return {"ok": False, "error": "quota_exceeded", "used": used, "limit": limit}
                result = await item_service.create_item(
                    db, user_id, ItemCreate(url=url), background_tasks
                )
                return {
                    "ok": True,
                    "id": str(result.id),
                    "title": result.title or url,
                    "source_type": result.source_type,
                    "status": result.status,
                }
            except Exception:
                logger.exception("save_url failed: url=%s", url)
                return {"ok": False, "error": "failed to save url"}

        return {}

    return executor


def _build_report_executor(db: AsyncSession, user_id: UUID, seen_ids: set[UUID]):
    """C（報告窗口）的 domain executor：create_report / revise_report / search_reports。"""
    created_report: dict | None = None

    async def executor(name: str, args: dict) -> dict:
        nonlocal created_report

        if name == "create_report":
            if created_report is not None:
                return {"draft": created_report, "ok": True}
            try:
                draft = await report_service.create_from_chat(
                    db, user_id,
                    title=args.get("title", "未命名報告"),
                    body_md=args.get("content", ""),
                    summary=args.get("summary"),
                    source_item_ids=[str(i) for i in seen_ids],
                )
                created_report = draft
                return {"draft": draft, "ok": True}
            except Exception:
                return {"draft": None, "ok": False}

        if name == "revise_report":
            rid = args.get("report_id")
            try:
                res = (
                    await report_service.revise_from_chat(
                        db, user_id, UUID(rid), args.get("instruction", "")
                    )
                    if rid
                    else None
                )
                return {"ok": res is not None, "report_id": rid}
            except Exception:
                return {"ok": False, "report_id": rid}

        if name == "search_reports":
            try:
                return await report_service.search_from_chat(
                    db, user_id,
                    query=args.get("query") or None,
                    limit=int(args.get("limit") or 5),
                )
            except Exception:
                logger.exception("search_reports failed")
                return []

        return {}

    return executor


def _build_trip_executor(db: AsyncSession, user_id: UUID, seen_ids: set[UUID]):
    """D（旅遊窗口）的 domain executor：create_trip / add_trip_card / revise_trip / search_trips。"""
    created_trip: dict | None = None

    async def executor(name: str, args: dict) -> dict:
        nonlocal created_trip

        if name == "create_trip":
            if created_trip is not None:
                return {"draft": created_trip, "ok": True}
            try:
                # 建立「空」行程；卡片由後續 add_trip_card 逐張新增
                draft = await trip_service.create_trip_from_chat(
                    db, user_id,
                    title=args.get("title", "未命名行程"),
                    summary=args.get("summary"),
                    start_date=args.get("start_date"),
                    end_date=args.get("end_date"),
                    source_item_ids=[str(i) for i in seen_ids],
                )
                created_trip = draft
                return {"draft": draft, "ok": True}
            except Exception:
                logger.exception("create_trip_from_chat failed")
                return {"draft": None, "ok": False}

        if name == "add_trip_card":
            # 卡片掛到本輪建立的行程（不信任模型給的 trip_id，避免誤寫他人行程）
            if created_trip is None:
                return {"ok": False}
            # 只接受本次實際檢索／預載過的知識 id（防模型亂編 id 寫到別人的知識）
            raw_src = args.get("source_item_ids") or []
            valid_src: list[str] = []
            for sid in raw_src if isinstance(raw_src, list) else []:
                try:
                    if UUID(str(sid)) in seen_ids:
                        valid_src.append(str(sid))
                except (ValueError, TypeError):
                    continue
            try:
                res = await trip_service.add_card_from_chat(
                    db, user_id, UUID(created_trip["id"]),
                    day=args.get("day"),
                    end_day=args.get("end_day"),
                    title=args.get("title", "未命名"),
                    place_name=args.get("place_name"),
                    category=args.get("category"),
                    emoji=args.get("emoji"),
                    start_time=args.get("start_time"),
                    note=args.get("note"),
                    source_item_ids=valid_src or None,
                )
                return {"ok": bool(res), "title": (res or {}).get("title")}
            except Exception:
                logger.exception("add_card_from_chat failed")
                return {"ok": False}

        if name == "search_trips":
            try:
                return await trip_service.search_trips_from_chat(
                    db, user_id,
                    query=args.get("query") or None,
                    limit=int(args.get("limit") or 5),
                )
            except Exception:
                logger.exception("search_trips failed")
                return []

        if name == "revise_trip":
            tid = args.get("trip_id")
            if not tid:
                return None
            try:
                return await trip_service.revise_trip_from_chat(
                    db, user_id, UUID(tid), args.get("instruction", "")
                )
            except Exception:
                logger.exception("revise_trip failed: trip_id=%s", tid)
                return None

        return {}

    return executor


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
    *,
    skip_user_message: bool = False,
    assistant_message_id: UUID | None = None,
):
    """
    LangGraph 分層 agentic SSE stream：A 監督者派工給 B/C/D 窗口。
    Emits: tool_call | tool_result | sources | report_draft | trip_draft | delta | done
    """
    logger.debug(
        "chat stream start: session=%s user=%s context_items=%d content=%r",
        session_id, user_id, len(context_item_ids or []), user_content[:120],
    )
    session = await crud_chat.get_session_with_messages(db, session_id, user_id)
    if not session:
        logger.debug("chat stream abort: session %s not found", session_id)
        yield _sse("error", {"message": "session not found"})
        return

    history = _build_history(session.messages)
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

    if not skip_user_message:
        await crud_chat.add_message(
            db, session_id, MessageRole.user, user_content,
            cited_item_ids=context_item_ids if context_item_ids else None,
        )

    # 把選定的知識節點當成初始脈絡餵給 A（否則 AI 看不到內容，會反問主題）
    preloaded_sources = [_to_chat_source(ui).model_dump(mode="json") for ui, _ in preloaded_items]
    preloaded_chunks = [
        {
            "item_id": str(ui.id),
            "title": ui.title or "(無標題)",
            "text": (ui.notes_md or "")[:4000],
            "tags": _item_tags(ui),
            "locations": _item_locations(ui),
        }
        for ui, _ in preloaded_items
    ]

    all_sources: list[dict] = list(preloaded_sources)

    knowledge_executor = _build_knowledge_executor(
        db, user_id, background_tasks, seen_ids, all_sources, cutoff, user_content,
        _item_tags, _item_locations,
    )
    report_executor = _build_report_executor(db, user_id, seen_ids)
    trip_executor = _build_trip_executor(db, user_id, seen_ids)

    # A 的訊息歷史：先放跨輪對話歷史，若有 preload 知識節點，用一組「假裝已經問過
    # B」的 function call / response 塞進去，讓 A 直接看到內容、不用再派工去問一次。
    messages: list[types.Content] = list(history)
    if preloaded_sources or preloaded_chunks:
        preload_tool = _TARGET_TO_TOOL["knowledge"]
        messages.append(model_turn(
            calls=[(preload_tool, {"event": "（使用者已選定的知識庫內容）"})],
        ))
        messages.append(tool_results(
            (preload_tool, {"items": preloaded_sources, "chunks": preloaded_chunks, "saved": []}),
        ))
    messages.append(user_turn(user_content))

    initial_state = {
        "messages": messages,
        "context_summary": context_summary,
        "round": 0,
        "max_rounds": _SUPERVISOR_MAX_ROUNDS,
        "dispatch_target": None,
        "dispatch_tool_name": None,
        "dispatch_event": None,
        "dispatch_context": None,
        "window_result": None,
        "final_reply": "",
        "finished": False,
    }
    config = {"configurable": {
        "knowledge_executor": knowledge_executor,
        "report_executor": report_executor,
        "trip_executor": trip_executor,
    }}

    from app.services.ai_service.graph import build_graph

    graph = build_graph()
    reply_text = ""
    process_steps: list[dict] = []
    dispatches: list[dict] = []
    pending_tool_call: dict | None = None
    pending_dispatch: dict | None = None

    try:
        async for mode, chunk in graph.astream(
            initial_state, config=config, stream_mode=["custom", "updates"]
        ):
            if mode == "custom":
                event = chunk["event"]
                data = chunk["data"]
                if event == "tool_call":
                    pending_tool_call = data
                elif event == "tool_result" and pending_tool_call is not None:
                    process_steps.append({"toolCall": pending_tool_call, "toolResult": data})
                    pending_tool_call = None
                yield _sse(event, data)
                continue

            # mode == "updates": {node_name: partial_state_returned_by_that_node}
            for node_name, partial in chunk.items():
                if node_name == "supervisor":
                    if partial.get("dispatch_target"):
                        pending_dispatch = {
                            "target": partial["dispatch_target"],
                            "event": partial.get("dispatch_event"),
                        }
                    if partial.get("finished"):
                        reply_text = partial.get("final_reply", "")
                elif node_name in ("knowledge", "report", "trip") and pending_dispatch is not None:
                    dispatches.append({
                        "target": pending_dispatch["target"],
                        "event": pending_dispatch["event"],
                        "result": partial.get("window_result"),
                    })
                    pending_dispatch = None
    except asyncio.CancelledError:
        # 使用者按停止 / 連線中斷 → generator 被取消，不持久化半截內容，乾淨拋出讓 Starlette 收尾
        logger.debug(
            "chat stream interrupted: session=%s partial_reply_len=%d (not persisted)",
            session_id, len(reply_text),
        )
        raise

    cited_ids = [str(i) for i in seen_ids]
    yield _sse("sources", all_sources)
    yield _sse("done", {})

    process_log = {"thinking": "", "steps": process_steps, "dispatches": dispatches}

    if assistant_message_id:
        await crud_chat.update_message(
            db, assistant_message_id, reply_text,
            cited_item_ids=[UUID(i) for i in cited_ids] if cited_ids else None,
            process_log=process_log,
            status="complete",
        )
    else:
        await crud_chat.add_message(
            db, session_id, MessageRole.assistant, reply_text,
            [UUID(i) for i in cited_ids] if cited_ids else None,
            process_log=process_log,
        )
    await crud_chat.touch_session(db, session_id)
    logger.debug(
        "chat stream persisted: session=%s reply_len=%d cited=%d",
        session_id, len(reply_text), len(cited_ids),
    )

    msg_count = await crud_chat.count_messages(db, session_id)
    if msg_count % 8 == 0:
        to_compress = history[:-8] if len(history) > 8 else history
        if to_compress:
            background_tasks.add_task(_compress_context, session_id, context_summary, to_compress)


def _build_history(msgs) -> list[types.Content]:
    """把 session 訊息轉成 LLM 對話歷史。

    對「每一則」有派工軌跡的 assistant 訊息都重放它的派工過程（dispatch_knowledge_base /
    dispatch_report_desk / dispatch_trip_desk 的 function call + 該窗口回傳的原始結果），
    不是只留最近一則——A 要能「綜合整個對話歷史」判斷這次事件該引用哪些先前查到的知識
    item_ids，需要每一輪查到的完整原始資料都還在（見 graph/supervisor.py 的
    _build_knowledge_index）。其餘訊息只放純文字以控制 token。

    DB 裡 process_log["dispatches"] 的形狀（{target, event, result}）是自家 schema，
    不隨底層訊息格式改變，所以舊資料照樣重放得出來。
    """
    # 只送已完成的訊息進歷史，排除 pending/streaming placeholder
    msgs = [m for m in msgs if getattr(m, "status", "complete") == "complete"]

    out: list[types.Content] = []
    for m in msgs:
        dispatches = (m.process_log or {}).get("dispatches") if m.role.value == "assistant" else None
        replayed = [
            (tool_name, d)
            for d in (dispatches or [])
            if (tool_name := _TARGET_TO_TOOL.get(d.get("target")))
        ]
        if replayed:
            out.append(model_turn(calls=[
                (tool_name, {"event": d.get("event") or ""}) for tool_name, d in replayed
            ]))
            out.append(tool_results(*[
                (tool_name, d.get("result") or {}) for tool_name, d in replayed
            ]))
            out.append(model_turn(text=m.content))
        elif m.role.value == "assistant":
            out.append(model_turn(text=m.content))
        else:
            out.append(user_turn(m.content))
    return out


def _sse(event: str, data) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def run_reply_background(
    assistant_message_id: UUID,
    session_id: UUID,
    user_id: UUID,
    user_content: str,
    context_item_ids: list[UUID],
) -> None:
    """
    背景執行 agentic stream，與 SSE 連線解耦。
    每個 SSE event 推入 StreamRegistry，完成後更新 DB。
    即使 SSE client 斷線，此 task 仍繼續到底。
    """
    from app.core.database import AsyncSessionLocal
    from app.services.stream_registry import stream_registry
    from fastapi import BackgroundTasks

    entry = stream_registry.get(assistant_message_id)
    if entry is None:
        logger.warning("run_reply_background: entry not found for %s", assistant_message_id)
        return

    # Mark as streaming in DB
    async with AsyncSessionLocal() as db:
        await crud_chat.update_message(db, assistant_message_id, "", status="streaming")

    try:
        async with AsyncSessionLocal() as db:
            bg = BackgroundTasks()
            async for event_str in stream_reply(
                db, session_id, user_id, user_content, bg,
                context_item_ids=context_item_ids,
                skip_user_message=True,
                assistant_message_id=assistant_message_id,
            ):
                entry.publish(event_str)
        # Close the SSE connection before running background tasks so the
        # frontend receives 'done' and the HTTP stream ends immediately.
        entry.complete()
        for task in bg.tasks:
            asyncio.create_task(task.func(*task.args, **task.kwargs))
    except Exception as exc:
        logger.exception("run_reply_background failed: message=%s", assistant_message_id)
        async with AsyncSessionLocal() as db:
            await crud_chat.update_message(db, assistant_message_id, "", status="failed")
        entry.fail(str(exc))
    finally:
        # Remove registry entry after a short delay to let late subscribers drain
        await asyncio.sleep(60)
        stream_registry.remove(assistant_message_id)


async def _compress_context(
    session_id: UUID,
    current_summary: str | None,
    old_messages: list[types.Content],
) -> None:
    from app.core.database import AsyncSessionLocal
    try:
        new_summary = await ai_service.compress_memory(current_summary, old_messages)
        async with AsyncSessionLocal() as db:
            await crud_chat.set_context_summary(db, session_id, new_summary)
    except Exception:
        pass
