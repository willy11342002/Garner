"""
chat_service：AI Chat 對話式 RAG 服務。

流程：
  用戶訊息 → agentic_chat_stream（原生 tool calling loop）→ 儲存訊息
  每 8 則訊息 → background task 壓縮 session context_summary
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("garner.chat")

from app.crud import chat as crud_chat
from app.crud import chunks as crud_chunks
from app.crud import items as crud_items
from app.models.chat import MessageRole
from app.models.user_item import UserItem
from app.schemas.chat import ChatSource
from app.services import ai_service
from app.services import report_service
from app.services import trip_service


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
    logger.debug(
        "chat stream start: session=%s user=%s context_items=%d content=%r",
        session_id, user_id, len(context_item_ids or []), user_content[:120],
    )
    session = await crud_chat.get_session_with_messages(db, session_id, user_id)
    if not session:
        logger.debug("chat stream abort: session %s not found", session_id)
        yield _sse("error", {"message": "session not found"})
        return

    if not session.title:
        title = user_content[:40] + ("…" if len(user_content) > 40 else "")
        await crud_chat.update_session(db, session_id, user_id, title=title)

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

    created_report: dict | None = None  # 防止同一輪 LLM 重複呼叫 create_report
    created_trip: dict | None = None  # 防止同一輪 LLM 重複呼叫 create_trip

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
                        "item_id": str(c.user_item_id),
                        "title": item_map[c.user_item_id].title if c.user_item_id in item_map else "(無標題)",
                        "text": c.text,
                        "tags": _item_tags(item_map[c.user_item_id]) if c.user_item_id in item_map else [],
                        "locations": _item_locations(item_map[c.user_item_id]) if c.user_item_id in item_map else [],
                    }
                    for c, _ in chunk_hits
                ]
            return {"items": items_out, "chunks": chunks_out}

        if name == "create_report":
            nonlocal created_report
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

        if name == "create_trip":
            nonlocal created_trip
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
            # 只接受本 session 實際檢索／預載過的知識 id（防模型亂編 id 寫到別人的知識）
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

        return {}

    # ── Agentic loop ─────────────────────────────────────────────────────────
    reply_text = ""
    process_steps: list[dict] = []
    cited_ids: list[str] = []

    await crud_chat.add_message(
        db, session_id, MessageRole.user, user_content,
        cited_item_ids=context_item_ids if context_item_ids else None,
    )

    # 把選定的知識節點當成初始脈絡餵給 LLM（否則 AI 看不到內容，會反問主題）
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

    try:
        async for event_str in ai_service.agentic_chat_stream(
            user_content, history, context_summary, execute_tool,
            preloaded_sources=preloaded_sources,
            preloaded_chunks=preloaded_chunks,
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
    except asyncio.CancelledError:
        # 使用者按停止 / 連線中斷 → generator 被取消，不持久化半截內容，乾淨拋出讓 Starlette 收尾
        logger.debug(
            "chat stream interrupted: session=%s partial_reply_len=%d (not persisted)",
            session_id, len(reply_text),
        )
        raise

    await crud_chat.add_message(
        db, session_id, MessageRole.assistant, reply_text,
        [UUID(i) for i in cited_ids] if cited_ids else None,
        process_log={"thinking": "", "steps": process_steps},
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


def _build_history(msgs) -> list[dict]:
    """把 session 訊息轉成 LLM 對話歷史。

    對「最近一則有檢索軌跡的 assistant」重放它的 tool-calling 過程（tool 參數 + 取得的
    item ids/titles），讓模型知道上一輪搜過什麼、拿到哪些 item，避免「重新生一份／微調」
    時又把同樣的 query 重搜一次。其餘訊息只放純文字以控制 token。
    """
    last_trace_idx = -1
    for i, m in enumerate(msgs):
        if m.role.value == "assistant" and m.process_log and m.process_log.get("steps"):
            last_trace_idx = i

    out: list[dict] = []
    for i, m in enumerate(msgs):
        if i == last_trace_idx:
            tool_calls: list[dict] = []
            tool_msgs: list[dict] = []
            for j, step in enumerate(m.process_log.get("steps") or []):
                tc = step.get("toolCall") or {}
                name = tc.get("name")
                if not name:
                    continue
                call_id = f"hist-{m.id}-{j}"
                args = {k: v for k, v in tc.items() if k != "name"}
                tool_calls.append({
                    "id": call_id,
                    "type": "function",
                    "function": {"name": name, "arguments": json.dumps(args, ensure_ascii=False)},
                })
                # toolResult 內含 count + titles（每筆有 id/title）→ 模型即知取得了哪些 item
                tool_msgs.append({
                    "role": "tool",
                    "tool_call_id": call_id,
                    "content": json.dumps(step.get("toolResult") or {}, ensure_ascii=False),
                })
            if tool_calls:
                out.append({"role": "assistant", "content": None, "tool_calls": tool_calls})
                out.extend(tool_msgs)
            out.append({"role": "assistant", "content": m.content})
        else:
            out.append({"role": m.role.value, "content": m.content})
    return out


def _sse(event: str, data) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def stream_reply_with_heartbeat(*args, heartbeat_interval: float = 15.0, **kwargs):
    """
    包一層 keepalive：串流靜默超過 heartbeat_interval 秒就送一個 SSE comment（`: ping`），
    避免前端 idle-timeout 把「慢但還活著」的 agentic 串流（工具呼叫/執行階段不發事件）誤判為斷線。
    前端 SSE parser 會略過 comment 行、收到任何 byte 就重置 idle timer，故前端不需改動。
    中斷時照常把 CancelledError 傳進 stream_reply（觸發其不持久化 + 中止 OpenRouter 串流）。
    """
    gen = stream_reply(*args, **kwargs)
    queue: asyncio.Queue = asyncio.Queue()
    _END = object()

    async def _pump():
        try:
            async for ev in gen:
                await queue.put(ev)
        except asyncio.CancelledError:
            raise
        except BaseException as e:  # 把例外搬到主流程重新拋出，保留 traceback
            await queue.put(e)
        else:
            await queue.put(_END)

    pump_task = asyncio.create_task(_pump())
    get_task: asyncio.Task | None = None
    try:
        while True:
            if get_task is None:
                get_task = asyncio.create_task(queue.get())
            # 逾時不取消 get_task（跨輪保留），避免 wait_for 取消造成漏事件的競態
            done, _ = await asyncio.wait({get_task}, timeout=heartbeat_interval)
            if not done:
                yield ": ping\n\n"  # SSE comment：純 keepalive，前端略過
                continue
            item = get_task.result()
            get_task = None
            if item is _END:
                break
            if isinstance(item, BaseException):
                raise item
            yield item
    finally:
        if get_task is not None:
            get_task.cancel()
        if not pump_task.done():
            pump_task.cancel()
        try:
            await pump_task
        except BaseException:
            pass


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
