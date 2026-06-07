"""
Quota dependencies — 以 FastAPI Depends 方式注入配額檢查。

只適用於「進 API 時就能判斷」的限制（次數上限、功能開關）。
影片長度限制無法在入口檢查（duration 要到 background task 打 YouTube API 才知道），
應在 item_service.create_item() 內查 plan → 取得 video_max_sec 傳給 background task。

用法（router 端）：
    from app.quota_depends import SaveQuota, ChatQuota, ExploreQuota, SearchAccess, ForkAccess

    @router.post("/")
    async def create_item(_quota: SaveQuota, ...): ...

    @router.get("/")
    async def search(_access: SearchAccess, ...): ...

    @router.post("/sessions/{session_id}/messages")
    async def send_message(_quota: ChatQuota, ...): ...
"""

from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import CurrentUser, DbSession
from app.models.content_object import ContentObject, SourceType
from app.models.plan_feature_limit import PlanFeatureLimit
from app.models.subscription import Subscription, SubscriptionStatus
from app.models.user_feature_usage import UserFeatureUsage
from app.models.user_item import UserItem
from app.models.plan import Plan


# ── Internal helpers ──────────────────────────────────────────────────────────


async def _get_plan(db: AsyncSession, user_id: UUID) -> tuple[UUID, str]:
    """Return (plan_id, plan_name). Falls back to the 'free' plan row."""
    result = await db.execute(
        select(Plan.id, Plan.name)
        .join(Subscription, Plan.id == Subscription.plan_id)
        .where(
            Subscription.user_id == user_id,
            Subscription.status.in_([SubscriptionStatus.active, SubscriptionStatus.trialing]),
        )
    )
    row = result.one_or_none()
    if row:
        return row.id, row.name
    free = await db.execute(select(Plan.id, Plan.name).where(Plan.name == "free"))
    free_row = free.one_or_none()
    if free_row:
        return free_row.id, free_row.name
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Free plan not configured")


async def _get_limit(db: AsyncSession, plan_id: UUID, feature: str) -> int | None:
    """Return the limit value for (plan_id, feature). None = unlimited."""
    result = await db.execute(
        select(PlanFeatureLimit.value).where(
            PlanFeatureLimit.plan_id == plan_id,
            PlanFeatureLimit.feature == feature,
        )
    )
    row = result.one_or_none()
    return row[0] if row is not None else None


async def _get_plan_with_period(
    db: AsyncSession, user_id: UUID
) -> tuple[UUID, str, datetime | None]:
    """一次查詢取得 plan_id、plan_name、period_end，合并 _get_plan + _get_period_end。"""
    result = await db.execute(
        select(Plan.id, Plan.name, Subscription.current_period_end)
        .join(Subscription, Plan.id == Subscription.plan_id)
        .where(
            Subscription.user_id == user_id,
            Subscription.status.in_([SubscriptionStatus.active, SubscriptionStatus.trialing]),
        )
    )
    row = result.one_or_none()
    if row:
        return row.id, row.name, row.current_period_end
    free = await db.execute(select(Plan.id, Plan.name).where(Plan.name == "free"))
    free_row = free.one_or_none()
    if free_row:
        return free_row.id, free_row.name, None
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Free plan not configured")


async def _get_all_limits(db: AsyncSession, plan_id: UUID) -> dict[str, int | None]:
    """一次撈出該 plan 所有 feature 的 limit，回傳 {feature: value}。"""
    result = await db.execute(
        select(PlanFeatureLimit.feature, PlanFeatureLimit.value)
        .where(PlanFeatureLimit.plan_id == plan_id)
    )
    return {row.feature: row.value for row in result.all()}


async def _get_multi_usage(
    db: AsyncSession,
    user_id: UUID,
    features: list[tuple[str, str]],
) -> dict[str, int]:
    """一次查多個 (feature, period_key)，回傳 {feature: count}，缺少的 feature 預設為 0。"""
    conditions = or_(*[
        and_(UserFeatureUsage.feature == f, UserFeatureUsage.period_key == p)
        for f, p in features
    ])
    result = await db.execute(
        select(UserFeatureUsage.feature, UserFeatureUsage.count)
        .where(UserFeatureUsage.user_id == user_id, conditions)
    )
    return {row.feature: row.count for row in result.all()}


async def _get_usage(db: AsyncSession, user_id: UUID, feature: str, period_key: str) -> int:
    result = await db.execute(
        select(UserFeatureUsage.count).where(
            UserFeatureUsage.user_id == user_id,
            UserFeatureUsage.feature == feature,
            UserFeatureUsage.period_key == period_key,
        )
    )
    return result.scalar_one_or_none() or 0


async def _increment(db: AsyncSession, user_id: UUID, feature: str, period_key: str) -> None:
    stmt = (
        pg_insert(UserFeatureUsage)
        .values(user_id=user_id, feature=feature, period_key=period_key, count=1)
        .on_conflict_do_update(
            index_elements=["user_id", "feature", "period_key"],
            set_={"count": UserFeatureUsage.count + 1},
        )
    )
    await db.execute(stmt)


def _monthly_key() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def _daily_key() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


async def _count_monthly_saves(db: AsyncSession, user_id: UUID) -> int:
    """Count active external-URL UserItems created this calendar month (UTC).
    Excludes user-written articles (source_type=article) since those use a separate endpoint
    with no quota gate and should not consume the URL save budget.
    """
    month_start = datetime.now(timezone.utc).replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )
    result = await db.execute(
        select(func.count())
        .select_from(UserItem)
        .join(UserItem.content)
        .where(
            UserItem.user_id == user_id,
            UserItem.saved_at >= month_start,
            UserItem.deleted_at.is_(None),
            ContentObject.source_type != SourceType.article,
        )
    )
    return result.scalar_one()


def _quota_exceeded(feature: str, used: int, limit: int, plan: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail={"feature": feature, "used": used, "limit": limit, "plan": plan},
    )


def _access_denied(feature: str, plan: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={"feature": feature, "plan": plan},
    )


# ── Public dependency functions ───────────────────────────────────────────────


async def check_save_quota(current_user: CurrentUser, db: DbSession) -> None:
    """
    Check-only（不 increment）。
    User item 創建後 saved_at 自動記錄，count 從 user_items 直接計算，無需手動維護。
    """
    user_id = UUID(current_user["sub"])
    plan_id, plan_name = await _get_plan(db, user_id)
    limit = await _get_limit(db, plan_id, "saves_monthly")
    if limit is None:
        return
    used = await _count_monthly_saves(db, user_id)
    if used >= limit:
        raise _quota_exceeded("saves_monthly", used, limit, plan_name)


async def check_chat_quota(current_user: CurrentUser, db: DbSession) -> None:
    """Check + increment。並發安全：在串流開始前就鎖定用量。"""
    user_id = UUID(current_user["sub"])
    plan_id, plan_name = await _get_plan(db, user_id)
    limit = await _get_limit(db, plan_id, "chat_daily")
    if limit is None:
        return
    period = _daily_key()
    used = await _get_usage(db, user_id, "chat_daily", period)
    if used >= limit:
        raise _quota_exceeded("chat_daily", used, limit, plan_name)
    await _increment(db, user_id, "chat_daily", period)
    await db.commit()


async def check_explore_quota(current_user: CurrentUser, db: DbSession) -> None:
    """Check + increment。Surprise / chain hop / chain full 各算一次。"""
    user_id = UUID(current_user["sub"])
    plan_id, plan_name = await _get_plan(db, user_id)
    limit = await _get_limit(db, plan_id, "explore_monthly")
    if limit is None:
        return
    period = _monthly_key()
    used = await _get_usage(db, user_id, "explore_monthly", period)
    if used >= limit:
        raise _quota_exceeded("explore_monthly", used, limit, plan_name)
    await _increment(db, user_id, "explore_monthly", period)
    await db.commit()


async def check_search_access(current_user: CurrentUser, db: DbSession) -> None:
    user_id = UUID(current_user["sub"])
    plan_id, plan_name = await _get_plan(db, user_id)
    limit = await _get_limit(db, plan_id, "search")
    if limit == 0:
        raise _access_denied("search", plan_name)


async def check_fork_access(current_user: CurrentUser, db: DbSession) -> None:
    user_id = UUID(current_user["sub"])
    plan_id, plan_name = await _get_plan(db, user_id)
    limit = await _get_limit(db, plan_id, "fork")
    if limit == 0:
        raise _access_denied("fork", plan_name)


async def get_video_max_sec(db: AsyncSession, user_id: UUID) -> int:
    """
    影片長度上限（秒）。供 item_service 查完 plan 後傳給 background task，
    不作為 Depends，因為 duration 在 background task 才能驗證。
    """
    plan_id, _ = await _get_plan(db, user_id)
    limit = await _get_limit(db, plan_id, "video_max_sec")
    return limit if limit is not None else 1200


# ── Annotated type aliases（在 router 直接當型別標注用）────────────────────────

SaveQuota = Annotated[None, Depends(check_save_quota)]
ChatQuota = Annotated[None, Depends(check_chat_quota)]
ExploreQuota = Annotated[None, Depends(check_explore_quota)]
SearchAccess = Annotated[None, Depends(check_search_access)]
ForkAccess = Annotated[None, Depends(check_fork_access)]
