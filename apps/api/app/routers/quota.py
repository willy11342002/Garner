from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import text

from app.dependencies import CurrentUser, DbSession
from app.quota_depends import _daily_key, _monthly_key

router = APIRouter()


class QuotaItem(BaseModel):
    used: int
    limit: int | None  # None = unlimited


class UsageSummary(BaseModel):
    plan: str
    period_end: datetime | None  # active subscription end date; None for free users
    saves: QuotaItem
    chat: QuotaItem
    explore: QuotaItem
    synthesis: QuotaItem
    search_enabled: bool
    fork_enabled: bool
    video_max_minutes: int


_QUOTA_SQL = text("""
WITH effective_plan AS (
    -- 有效訂閱的 plan
    SELECT p.id AS plan_id, p.name AS plan_name, s.current_period_end
    FROM subscriptions s
    JOIN plans p ON p.id = s.plan_id
    WHERE s.user_id = :user_id
      AND s.status IN ('active', 'trialing')
      AND s.current_period_end > NOW()
    UNION ALL
    -- 無訂閱時 fallback 到 free plan
    SELECT p.id, p.name, NULL::timestamptz
    FROM plans p
    WHERE p.name = 'free'
      AND NOT EXISTS (
          SELECT 1 FROM subscriptions s2
          WHERE s2.user_id = :user_id
            AND s2.status IN ('active', 'trialing')
            AND s2.current_period_end > NOW()
      )
    LIMIT 1
)
SELECT
    ep.plan_name,
    ep.current_period_end,
    -- saves：直接 count user_items，不走 user_feature_usage
    (SELECT COUNT(*)::int
     FROM user_items ui
     JOIN content_objects co ON co.id = ui.content_id
     WHERE ui.user_id  = :user_id
       AND ui.saved_at >= :month_start
       AND ui.deleted_at IS NULL
       AND co.source_type != 'article'
    ) AS saves_used,
    -- usage（各走 unique index point lookup）
    COALESCE((SELECT ufu.count FROM user_feature_usage ufu
              WHERE ufu.user_id = :user_id AND ufu.feature = 'chat_daily'
                AND ufu.period_key = :daily_key), 0)    AS chat_used,
    COALESCE((SELECT ufu.count FROM user_feature_usage ufu
              WHERE ufu.user_id = :user_id AND ufu.feature = 'explore_monthly'
                AND ufu.period_key = :monthly_key), 0)  AS explore_used,
    COALESCE((SELECT ufu.count FROM user_feature_usage ufu
              WHERE ufu.user_id = :user_id AND ufu.feature = 'synthesis_monthly'
                AND ufu.period_key = :monthly_key), 0)  AS synthesis_used,
    -- limits（各走 PK index point lookup）
    (SELECT pfl.value FROM plan_feature_limits pfl
     WHERE pfl.plan_id = ep.plan_id AND pfl.feature = 'saves_monthly')      AS saves_limit,
    (SELECT pfl.value FROM plan_feature_limits pfl
     WHERE pfl.plan_id = ep.plan_id AND pfl.feature = 'chat_daily')         AS chat_limit,
    (SELECT pfl.value FROM plan_feature_limits pfl
     WHERE pfl.plan_id = ep.plan_id AND pfl.feature = 'explore_monthly')    AS explore_limit,
    (SELECT pfl.value FROM plan_feature_limits pfl
     WHERE pfl.plan_id = ep.plan_id AND pfl.feature = 'synthesis_monthly')  AS synthesis_limit,
    (SELECT pfl.value FROM plan_feature_limits pfl
     WHERE pfl.plan_id = ep.plan_id AND pfl.feature = 'video_max_sec')   AS video_max_sec,
    (SELECT pfl.value FROM plan_feature_limits pfl
     WHERE pfl.plan_id = ep.plan_id AND pfl.feature = 'search')          AS search_val,
    (SELECT pfl.value FROM plan_feature_limits pfl
     WHERE pfl.plan_id = ep.plan_id AND pfl.feature = 'fork')            AS fork_val
FROM effective_plan ep
LIMIT 1
""")


@router.get("/me", response_model=UsageSummary)
async def get_my_quota(current_user: CurrentUser, db: DbSession):
    user_id = UUID(current_user["sub"])
    month_start = datetime.now(timezone.utc).replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )

    row = (await db.execute(
        _QUOTA_SQL,
        {
            "user_id": user_id,
            "month_start": month_start,
            "daily_key": _daily_key(),
            "monthly_key": _monthly_key(),
        },
    )).mappings().one()

    video_max_sec = row["video_max_sec"] or 1200

    return UsageSummary(
        plan=row["plan_name"],
        period_end=row["current_period_end"],
        saves=QuotaItem(used=row["saves_used"],           limit=row["saves_limit"]),
        chat=QuotaItem(used=row["chat_used"],              limit=row["chat_limit"]),
        explore=QuotaItem(used=row["explore_used"],        limit=row["explore_limit"]),
        synthesis=QuotaItem(used=row["synthesis_used"],    limit=row["synthesis_limit"]),
        search_enabled=bool(row["search_val"]),
        fork_enabled=bool(row["fork_val"]),
        video_max_minutes=video_max_sec // 60,
    )
