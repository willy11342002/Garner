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
