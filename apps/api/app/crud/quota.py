"""配額彙總查詢。

`quota_depends` 用 ORM 一項一項查（進 API 時只需要判斷單一限制），
這裡則是 /quota/me 用的彙總查詢：一次 round-trip 把 plan、三種用量、
四種限制全部撈齊，避免前端一個畫面打好幾次 DB。兩者刻意分開。
"""

from collections.abc import Mapping
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

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
    -- saves：count user_items + reanalyze/landmark 的 user_feature_usage 計次
    ((SELECT COUNT(*)::int
      FROM user_items ui
      WHERE ui.user_id  = :user_id
        AND ui.saved_at >= :month_start
        AND ui.deleted_at IS NULL
        AND ui.source_type != 'article')
     + COALESCE((SELECT ufu.count FROM user_feature_usage ufu
                 WHERE ufu.user_id = :user_id AND ufu.feature = 'saves_monthly'
                   AND ufu.period_key = :monthly_key), 0)
    ) AS saves_used,
    -- usage（各走 unique index point lookup）
    COALESCE((SELECT ufu.count FROM user_feature_usage ufu
              WHERE ufu.user_id = :user_id AND ufu.feature = 'chat_monthly'
                AND ufu.period_key = :monthly_key), 0)  AS chat_used,
    COALESCE((SELECT ufu.count FROM user_feature_usage ufu
              WHERE ufu.user_id = :user_id AND ufu.feature = 'synthesis_monthly'
                AND ufu.period_key = :monthly_key), 0)  AS synthesis_used,
    -- limits（各走 PK index point lookup）
    (SELECT pfl.value FROM plan_feature_limits pfl
     WHERE pfl.plan_id = ep.plan_id AND pfl.feature = 'saves_monthly')      AS saves_limit,
    (SELECT pfl.value FROM plan_feature_limits pfl
     WHERE pfl.plan_id = ep.plan_id AND pfl.feature = 'chat_monthly')       AS chat_limit,
    (SELECT pfl.value FROM plan_feature_limits pfl
     WHERE pfl.plan_id = ep.plan_id AND pfl.feature = 'synthesis_monthly')  AS synthesis_limit,
    (SELECT pfl.value FROM plan_feature_limits pfl
     WHERE pfl.plan_id = ep.plan_id AND pfl.feature = 'video_max_sec')   AS video_max_sec,
    (SELECT pfl.value FROM plan_feature_limits pfl
     WHERE pfl.plan_id = ep.plan_id AND pfl.feature = 'search')          AS search_val
FROM effective_plan ep
LIMIT 1
""")


async def get_usage_summary(
    db: AsyncSession,
    user_id: UUID,
    month_start: datetime,
    monthly_key: str,
) -> Mapping[str, Any]:
    """一次撈齊 plan / 用量 / 限制。回傳 row mapping，欄位名見上方 SQL 的 AS 別名。"""
    return (await db.execute(
        _QUOTA_SQL,
        {
            "user_id": user_id,
            "month_start": month_start,
            "monthly_key": monthly_key,
        },
    )).mappings().one()
