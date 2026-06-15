from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.crud import reports as crud_reports
from app.dependencies import CurrentUser, DbSession
from app.schemas.report import ReportListItem, ReportRead, ReportReviseRequest, ReportUpdate
from app.services import report_service

router = APIRouter()


@router.get("/", response_model=list[ReportListItem])
async def list_reports(current_user: CurrentUser, db: DbSession):
    return await report_service.list_reports(db, UUID(current_user["sub"]))


@router.get("/{report_id}", response_model=ReportRead)
async def get_report(report_id: UUID, current_user: CurrentUser, db: DbSession):
    report = await report_service.get_report(db, UUID(current_user["sub"]), report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@router.patch("/{report_id}", response_model=ReportRead)
async def update_report(
    report_id: UUID, data: ReportUpdate, current_user: CurrentUser, db: DbSession
):
    """人類手動編輯（title / body_md）。"""
    report = await report_service.update_by_user(
        db, UUID(current_user["sub"]), report_id, title=data.title, body_md=data.body_md
    )
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@router.post("/{report_id}/revise", response_model=ReportRead)
async def revise_report(
    report_id: UUID, data: ReportReviseRequest, current_user: CurrentUser, db: DbSession
):
    """AI 依指示修改目前內文（保留人類編輯）。"""
    report = await report_service.revise(
        db, UUID(current_user["sub"]), report_id, data.instruction
    )
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@router.post("/{report_id}/regenerate", response_model=ReportRead)
async def regenerate_report(report_id: UUID, current_user: CurrentUser, db: DbSession):
    """AI 從來源 items 重新生成（覆蓋現有內文）。"""
    report = await report_service.regenerate(db, UUID(current_user["sub"]), report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_report(report_id: UUID, current_user: CurrentUser, db: DbSession):
    report = await crud_reports.get_one(db, UUID(current_user["sub"]), report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    await crud_reports.delete(db, report)
