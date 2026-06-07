"""refactor plan limits: unify into plan_feature_limits, drop whisper_usage

- plan_feature_limits.plan (string) → plan_id (UUID FK → plans.id)
- drop plans.max_saves_per_month, max_storage_mb, whisper_daily_limit_seconds
- drop whisper_usage table

Revision ID: 0024
Revises: 0023
Create Date: 2026-06-07
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0024"
down_revision: Union[str, None] = "0023"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 0. Ensure 'free' and 'pro' plan rows exist (idempotent) ─────────────
    op.execute("""
        INSERT INTO plans (id, name, price_monthly, is_active)
        SELECT gen_random_uuid(), 'free', 0, true
        WHERE NOT EXISTS (SELECT 1 FROM plans WHERE name = 'free')
    """)
    op.execute("""
        INSERT INTO plans (id, name, price_monthly, is_active)
        SELECT gen_random_uuid(), 'pro', 0, true
        WHERE NOT EXISTS (SELECT 1 FROM plans WHERE name = 'pro')
    """)

    # ── 1. plan_feature_limits: string plan → UUID plan_id ───────────────────
    op.add_column(
        "plan_feature_limits",
        sa.Column("plan_id", sa.UUID(), nullable=True),
    )

    op.execute("""
        UPDATE plan_feature_limits pfl
        SET plan_id = p.id
        FROM plans p
        WHERE p.name = pfl.plan
    """)

    op.alter_column("plan_feature_limits", "plan_id", nullable=False)

    op.drop_constraint("plan_feature_limits_pkey", "plan_feature_limits", type_="primary")
    op.drop_column("plan_feature_limits", "plan")

    op.create_foreign_key(
        "fk_plan_feature_limits_plan_id",
        "plan_feature_limits", "plans",
        ["plan_id"], ["id"],
    )
    op.create_primary_key(
        "plan_feature_limits_pkey",
        "plan_feature_limits",
        ["plan_id", "feature"],
    )

    # ── 2. Remove limit columns from plans ───────────────────────────────────
    op.drop_column("plans", "max_saves_per_month")
    op.drop_column("plans", "max_storage_mb")
    op.drop_column("plans", "whisper_daily_limit_seconds")

    # ── 3. Drop whisper_usage table ──────────────────────────────────────────
    op.drop_index("ix_whisper_usage_user_id", table_name="whisper_usage")
    op.drop_index("ix_whisper_usage_date", table_name="whisper_usage")
    op.drop_table("whisper_usage")


def downgrade() -> None:
    # ── 1. Recreate whisper_usage ─────────────────────────────────────────────
    op.create_table(
        "whisper_usage",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("used_seconds", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_whisper_usage_date", "whisper_usage", ["date"])
    op.create_index("ix_whisper_usage_user_id", "whisper_usage", ["user_id"])

    # ── 2. Restore limit columns to plans ────────────────────────────────────
    op.add_column("plans", sa.Column("max_saves_per_month", sa.Integer(), nullable=True))
    op.add_column("plans", sa.Column("max_storage_mb", sa.Integer(), nullable=True))
    op.add_column(
        "plans",
        sa.Column("whisper_daily_limit_seconds", sa.Integer(), nullable=False, server_default="3600"),
    )

    # ── 3. plan_feature_limits: UUID plan_id → string plan ───────────────────
    op.drop_constraint("fk_plan_feature_limits_plan_id", "plan_feature_limits", type_="foreignkey")
    op.drop_constraint("plan_feature_limits_pkey", "plan_feature_limits", type_="primary")

    op.add_column(
        "plan_feature_limits",
        sa.Column("plan", sa.String(20), nullable=True),
    )

    op.execute("""
        UPDATE plan_feature_limits pfl
        SET plan = p.name
        FROM plans p
        WHERE p.id = pfl.plan_id
    """)

    op.alter_column("plan_feature_limits", "plan", nullable=False)
    op.drop_column("plan_feature_limits", "plan_id")

    op.create_primary_key(
        "plan_feature_limits_pkey",
        "plan_feature_limits",
        ["plan", "feature"],
    )
