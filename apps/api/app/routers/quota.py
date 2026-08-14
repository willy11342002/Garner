from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel

from app.crud import quota as crud_quota
from app.dependencies import CurrentUser, DbSession
from app.quota_depends import monthly_key

router = APIRouter()


class QuotaItem(BaseModel):
    used: int
    limit: int | None  # None = unlimited


class UsageSummary(BaseModel):
    plan: str
    period_end: datetime | None  # active subscription end date; None for free users
    saves: QuotaItem
    chat: QuotaItem
    synthesis: QuotaItem
    search_enabled: bool
    video_max_minutes: int


@router.get("/me", response_model=UsageSummary)
async def get_my_quota(current_user: CurrentUser, db: DbSession):
    user_id = UUID(current_user["sub"])
    month_start = datetime.now(timezone.utc).replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )

    row = await crud_quota.get_usage_summary(db, user_id, month_start, monthly_key())

    video_max_sec = row["video_max_sec"] or 1200

    return UsageSummary(
        plan=row["plan_name"],
        period_end=row["current_period_end"],
        saves=QuotaItem(used=row["saves_used"],           limit=row["saves_limit"]),
        chat=QuotaItem(used=row["chat_used"],              limit=row["chat_limit"]),
        synthesis=QuotaItem(used=row["synthesis_used"],    limit=row["synthesis_limit"]),
        search_enabled=bool(row["search_val"]),
        video_max_minutes=video_max_sec // 60,
    )
