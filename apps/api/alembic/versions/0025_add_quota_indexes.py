"""add quota-related indexes

1. plans(name) UNIQUE          — free plan fallback lookup
2. subscriptions(user_id, status)  — plan lookup filter
3. user_items partial index (user_id, saved_at) WHERE deleted_at IS NULL
   — monthly saves count 不需要再 heap-filter 軟刪除列

Revision ID: 0025
Revises: 0024
Create Date: 2026-06-07
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0025"
down_revision: Union[str, None] = "0024"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 0. 去重 plans（保留各 name 最小的 id）──────────────────────────────────
    # subscriptions 先改指向正規 plan，再刪多餘的 plan_feature_limits 和 plans

    op.execute("""
        WITH canonical AS (
            SELECT DISTINCT ON (name) id, name
            FROM plans
            ORDER BY name, id
        ),
        duplicates AS (
            SELECT p.id AS dup_id, c.id AS canonical_id
            FROM plans p
            JOIN canonical c ON c.name = p.name AND c.id <> p.id
        )
        UPDATE subscriptions
        SET plan_id = d.canonical_id
        FROM duplicates d
        WHERE subscriptions.plan_id = d.dup_id
    """)

    op.execute("""
        WITH canonical AS (
            SELECT DISTINCT ON (name) id
            FROM plans
            ORDER BY name, id
        )
        DELETE FROM plan_feature_limits
        WHERE plan_id NOT IN (SELECT id FROM canonical)
    """)

    op.execute("""
        WITH canonical AS (
            SELECT DISTINCT ON (name) id
            FROM plans
            ORDER BY name, id
        )
        DELETE FROM plans
        WHERE id NOT IN (SELECT id FROM canonical)
    """)

    # ── 1. plans.name UNIQUE index ────────────────────────────────────────────
    op.create_index(
        "ix_plans_name",
        "plans", ["name"],
        unique=True,
    )

    # subscriptions(user_id, status) — 大部分查詢同時過濾兩個欄位
    op.create_index(
        "ix_subscriptions_user_id_status",
        "subscriptions", ["user_id", "status"],
    )

    # user_items partial index：只索引「未軟刪除」的列，讓 monthly saves count 直接命中
    op.execute("""
        CREATE INDEX ix_user_items_active_user_saved_at
        ON user_items (user_id, saved_at)
        WHERE deleted_at IS NULL
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_user_items_active_user_saved_at")
    op.drop_index("ix_subscriptions_user_id_status", table_name="subscriptions")
    op.drop_index("ix_plans_name", table_name="plans")
