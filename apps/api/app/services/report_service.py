"""report_service：AI 產出層（報告）的業務邏輯。

職責：串接 ai_service 生成/revise → crud.reports 寫入 → 解析 provenance。
嚴格不 chunk/embed（產出永不進語料）。
"""
from uuid import UUID

from google.genai import types
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import reports as crud_reports
from app.models.report import Report
from app.models.user_item import UserItem
from app.schemas.report import ReportListItem, ReportRead, ReportSourceItem
from app.services import ai_service


def _to_source_item(ui: UserItem) -> ReportSourceItem:
    return ReportSourceItem(
        id=ui.id,
        title=ui.title,
        url=ui.url,
        thumbnail_url=ui.thumbnail_url,
        source_type=ui.source_type,
    )


async def _to_read(db: AsyncSession, user_id: UUID, report: Report) -> ReportRead:
    sources = await crud_reports.resolve_sources(db, user_id, report.source_item_ids)
    return ReportRead(
        id=report.id,
        title=report.title,
        body_md=report.body_md,
        summary=report.summary,
        sources=[_to_source_item(s) for s in sources],
        last_edited_by=report.last_edited_by,
        created_at=report.created_at,
        updated_at=report.updated_at,
    )


# ── Report AI FAB (SSE streaming) ──────────────────────────────────────────
#
# 懸浮球跟 chat 走同一顆引擎（chat_service.run_scoped_agent_stream → A 監督者 →
# B/C/D 窗口），所以這裡不再自己宣告工具或 prompt —— 工具集是 graph/windows/report.py
# 的那一份，唯一的差別是帶上「使用者正在編輯這份報告」的 scope。


async def ai_edit_report_stream(
    db: AsyncSession,
    user_id: UUID,
    report_id: UUID,
    instruction: str,
    history: list[dict] | None = None,
):
    """報告頁 AI 懸浮球：帶 scope 跑完整分層 agent（SSE 串流）。"""
    from app.services import chat_service
    from app.services.ai_service._client import _sse

    scope = await build_report_scope(db, user_id, report_id)
    if scope is None:
        yield _sse("error", {"message": "Report not found"})
        return

    async for ev in chat_service.run_scoped_agent_stream(
        db, user_id, instruction, scope,
        scope_report_id=report_id,
        history=history,
    ):
        yield ev


# ── chat tool 入口 ──────────────────────────────────────────────────────────


def _embed_text_for_report(report: Report) -> str:
    """組合 report 的 embedding 文本：title + summary（或 body 前 500 字）。"""
    parts = [report.title]
    if report.summary:
        parts.append(report.summary)
    elif report.body_md:
        parts.append(report.body_md[:500])
    return " ".join(parts)


async def _embed_report_bg(report_id: UUID, user_id: UUID, text: str) -> None:
    """背景更新 report embedding，使用獨立 session。"""
    import asyncio
    from app.core.database import AsyncSessionLocal
    try:
        embedding = await ai_service.embed(text)
        async with AsyncSessionLocal() as db:
            report = await crud_reports.get_one(db, user_id, report_id)
            if report:
                await crud_reports.update_embedding(db, report, embedding)
    except Exception:
        import logging
        logging.getLogger(__name__).exception("report embed failed for %s", report_id)


async def search_from_chat(
    db: AsyncSession,
    user_id: UUID,
    query: str | None,
    limit: int = 5,
) -> list[dict]:
    """chat 的 search_reports 工具用：有 query 時語意搜尋，否則列最近幾筆。"""
    if query:
        embedding = await ai_service.embed(query)
        rows = await crud_reports.semantic_search(db, user_id, embedding, limit=limit)
        if not rows:
            rows = await crud_reports.list_by_user(db, user_id)
            rows = rows[:limit]
    else:
        rows = await crud_reports.list_by_user(db, user_id)
        rows = rows[:limit]
    return [
        {
            "id": str(r.id),
            "title": r.title,
            "summary": r.summary,
            "updated_at": r.updated_at.isoformat(),
        }
        for r in rows
    ]


async def create_from_chat(
    db: AsyncSession,
    user_id: UUID,
    *,
    title: str,
    body_md: str,
    summary: str | None = None,
    source_item_ids: list | None = None,
) -> dict:
    """chat 的 create_report 工具用：LLM 已產好內文，這裡只負責持久化。

    回傳精簡 dict 給前端卡片（不含完整 body 也行，但帶上方便預覽）。
    """
    import asyncio
    report = await crud_reports.create(
        db,
        user_id,
        title=title,
        body_md=body_md,
        summary=summary,
        source_item_ids=source_item_ids,
        last_edited_by="ai",
    )
    text = _embed_text_for_report(report)
    asyncio.create_task(_embed_report_bg(report.id, user_id, text))
    return {
        "id": str(report.id),
        "title": report.title,
        "summary": report.summary,
    }


async def build_report_scope(
    db: AsyncSession, user_id: UUID, report_id: UUID
) -> dict | None:
    """組出「使用者正在編輯這份報告」要交給 graph 的 scope。

    brief 帶報告全文（截 16000 字），C 窗口的 update_report 是整篇覆寫，
    必須看得到現況才能在既有內文上接續修改而不是砍掉重寫。
    無權限或報告不存在時回 None。
    """
    report = await crud_reports.get_one(db, user_id, report_id)
    if report is None:
        return None
    return {
        "kind": "report",
        "id": str(report_id),
        "brief": f"報告標題：{report.title}\n\n目前內文：\n{(report.body_md or '')[:16000]}",
    }


async def update_report_from_chat(
    db: AsyncSession,
    user_id: UUID,
    report_id: UUID,
    title: str | None,
    body_md: str,
) -> dict:
    """C 窗口的 update_report：整篇覆寫，回傳含 _report 的結果供前端即時更新。"""
    import asyncio
    report = await crud_reports.get_one(db, user_id, report_id)
    if report is None:
        return {"ok": False, "error": "report not found"}
    await crud_reports.update(
        db, report, title=title or None, body_md=body_md, last_edited_by="ai"
    )
    asyncio.create_task(
        _embed_report_bg(report.id, user_id, _embed_text_for_report(report))
    )
    read = await _to_read(db, user_id, report)
    return {"ok": True, "_report": read.model_dump(mode="json")}


# ── REST 入口 ───────────────────────────────────────────────────────────────


async def list_reports(db: AsyncSession, user_id: UUID) -> list[ReportListItem]:
    rows = await crud_reports.list_by_user(db, user_id)
    return [
        ReportListItem(
            id=r.id,
            title=r.title,
            summary=r.summary,
            source_count=len(r.source_item_ids or []),
            last_edited_by=r.last_edited_by,
            created_at=r.created_at,
            updated_at=r.updated_at,
        )
        for r in rows
    ]


async def get_report(db: AsyncSession, user_id: UUID, report_id: UUID) -> ReportRead | None:
    report = await crud_reports.get_one(db, user_id, report_id)
    if report is None:
        return None
    return await _to_read(db, user_id, report)


async def update_by_user(
    db: AsyncSession,
    user_id: UUID,
    report_id: UUID,
    *,
    title: str | None = None,
    body_md: str | None = None,
) -> ReportRead | None:
    """人類手動編輯。"""
    import asyncio
    report = await crud_reports.get_one(db, user_id, report_id)
    if report is None:
        return None
    await crud_reports.update(
        db, report, title=title, body_md=body_md, last_edited_by="user"
    )
    text = _embed_text_for_report(report)
    asyncio.create_task(_embed_report_bg(report.id, user_id, text))
    return await _to_read(db, user_id, report)


async def revise(
    db: AsyncSession, user_id: UUID, report_id: UUID, instruction: str
) -> ReportRead | None:
    """AI 依指示修改目前內文（保留人類編輯）。"""
    report = await crud_reports.get_one(db, user_id, report_id)
    if report is None:
        return None
    new_body = await ai_service.revise_text(report.body_md, instruction)
    await crud_reports.update(db, report, body_md=new_body, last_edited_by="ai")
    return await _to_read(db, user_id, report)


async def regenerate(
    db: AsyncSession, user_id: UUID, report_id: UUID
) -> ReportRead | None:
    """AI 從來源 items 重新生成（會覆蓋現有內文，前端送出前須警告）。"""
    report = await crud_reports.get_one(db, user_id, report_id)
    if report is None:
        return None
    sources = await crud_reports.resolve_sources(db, user_id, report.source_item_ids)
    source_texts = [
        f"# {s.title or '(無標題)'}\n{s.notes_md or ''}".strip() for s in sources
    ]
    result = await ai_service.generate_report_body(report.title, source_texts)
    await crud_reports.update(
        db,
        report,
        title=result.get("title") or report.title,
        body_md=result.get("body_md") or report.body_md,
        summary=result.get("summary"),
        last_edited_by="ai",
    )
    return await _to_read(db, user_id, report)
