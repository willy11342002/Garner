from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel

from app.dependencies import CurrentUser, DbSession
from app.quota_depends import (
    _count_monthly_saves,
    _daily_key,
    _get_limit,
    _get_plan,
    _get_usage,
    _monthly_key,
)

router = APIRouter()


class QuotaItem(BaseModel):
    used: int
    limit: int | None  # None = unlimited


class UsageSummary(BaseModel):
    plan: str
    saves: QuotaItem
    chat: QuotaItem
    explore: QuotaItem
    search_enabled: bool
    fork_enabled: bool
    video_max_minutes: int


@router.get("/me", response_model=UsageSummary)
async def get_my_quota(current_user: CurrentUser, db: DbSession):
    user_id = UUID(current_user["sub"])
    plan = await _get_plan(db, user_id)

    saves_limit   = await _get_limit(db, plan, "saves_monthly")
    chat_limit    = await _get_limit(db, plan, "chat_daily")
    explore_limit = await _get_limit(db, plan, "explore_monthly")
    video_max_sec = await _get_limit(db, plan, "video_max_sec") or 1200
    search_val    = await _get_limit(db, plan, "search")
    fork_val      = await _get_limit(db, plan, "fork")

    saves_used   = await _count_monthly_saves(db, user_id)
    chat_used    = await _get_usage(db, user_id, "chat_daily",      _daily_key())
    explore_used = await _get_usage(db, user_id, "explore_monthly", _monthly_key())

    return UsageSummary(
        plan=plan,
        saves=QuotaItem(used=saves_used, limit=saves_limit),
        chat=QuotaItem(used=chat_used, limit=chat_limit),
        explore=QuotaItem(used=explore_used, limit=explore_limit),
        search_enabled=bool(search_val),
        fork_enabled=bool(fork_val),
        video_max_minutes=video_max_sec // 60,
    )
