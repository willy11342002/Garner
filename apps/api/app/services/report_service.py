"""report_service：AI 產出層（報告）的業務邏輯。

職責：串接 ai_service 生成/revise → crud.reports 寫入 → 解析 provenance。
嚴格不 chunk/embed（產出永不進語料）。
"""
from uuid import UUID

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

_REPORT_EDIT_SYSTEM = """\
你是一個 AI 助理，負責幫用戶修改他們的報告。
用戶會提供修改指令，你可以：
1. 使用 search 工具查詢用戶的個人知識庫，補充相關資料
2. 使用 update_report 工具更新報告標題（可選）與內文（必填）

報告標題：{title}

目前報告內文：
{body_md}
"""

_REPORT_EDIT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search",
            "description": "搜尋用戶的個人知識庫，找相關文章、筆記、研究資料。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "查詢字串"},
                    "limit": {"type": "integer", "description": "回傳筆數（預設 5）", "default": 5},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_report",
            "description": "更新報告的標題（可選）和完整 Markdown 內文。",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "新標題，不更改時省略"},
                    "body_md": {"type": "string", "description": "完整的 Markdown 內文（含所有修改）"},
                },
                "required": ["body_md"],
            },
        },
    },
]


async def ai_edit_report_stream(
    db: AsyncSession,
    user_id: UUID,
    report_id: UUID,
    instruction: str,
    history: list[dict] | None = None,
):
    """SSE streaming agentic report edit (search + update_report tools)."""
    from app.services.ai_service.tools import stream_tool_loop
    from app.services.ai_service._client import _sse

    report = await crud_reports.get_one(db, user_id, report_id)
    if report is None:
        yield _sse("error", {"message": "Report not found"})
        return

    system = _REPORT_EDIT_SYSTEM.format(
        title=report.title,
        body_md=(report.body_md or "")[:16000],
    )

    async def execute_tool(name: str, args: dict) -> dict:
        if name == "search":
            from app.services.chat_service import rag_retrieve
            query = args.get("query", "")
            limit = int(args.get("limit", 5))
            hits = await rag_retrieve(db, user_id, query, limit=limit)
            items_out = [
                {
                    "id": str(ui.id),
                    "title": ui.title or "",
                    "summary": ui.summary or "",
                    "tags": [t.name_zh for t in (ui.tags or [])],
                }
                for ui, _ in hits
            ]
            return {"count": len(items_out), "items": items_out}

        if name == "update_report":
            new_title = args.get("title") or None
            new_body = args.get("body_md", "")
            await crud_reports.update(
                db, report,
                title=new_title,
                body_md=new_body,
                last_edited_by="ai",
            )
            read = await _to_read(db, user_id, report)
            return {"ok": True, "_report": read.model_dump(mode="json")}

        return {"ok": False, "error": f"unknown tool: {name}"}

    async for sse in stream_tool_loop(system, instruction, _REPORT_EDIT_TOOLS, execute_tool, history=history):
        yield sse


# ── chat tool 入口 ──────────────────────────────────────────────────────────


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
    report = await crud_reports.create(
        db,
        user_id,
        title=title,
        body_md=body_md,
        summary=summary,
        source_item_ids=source_item_ids,
        last_edited_by="ai",
    )
    return {
        "id": str(report.id),
        "title": report.title,
        "summary": report.summary,
    }


async def revise_from_chat(
    db: AsyncSession, user_id: UUID, report_id: UUID, instruction: str
) -> dict | None:
    """chat 的 revise_report 工具用：對既有報告做 AI 修改（保留人類編輯，在其上接續）。"""
    report = await crud_reports.get_one(db, user_id, report_id)
    if report is None:
        return None
    new_body = await ai_service.revise_text(report.body_md, instruction)
    await crud_reports.update(db, report, body_md=new_body, last_edited_by="ai")
    return {"id": str(report.id), "title": report.title}


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
    report = await crud_reports.get_one(db, user_id, report_id)
    if report is None:
        return None
    await crud_reports.update(
        db, report, title=title, body_md=body_md, last_edited_by="user"
    )
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
