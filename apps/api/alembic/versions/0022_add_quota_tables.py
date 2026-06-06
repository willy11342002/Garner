"""add quota tables: plan_feature_limits + user_feature_usage

Revision ID: 0022
Revises: d09c652727cb
Create Date: 2026-06-06
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0022"
down_revision: Union[str, None] = "d09c652727cb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── plan_feature_limits ──────────────────────────────────────────────────
    op.create_table(
        "plan_feature_limits",
        sa.Column("plan", sa.String(20), nullable=False),
        sa.Column("feature", sa.String(40), nullable=False),
        sa.Column("value", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("plan", "feature"),
    )

    # ── user_feature_usage ───────────────────────────────────────────────────
    op.create_table(
        "user_feature_usage",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("feature", sa.String(40), nullable=False),
        sa.Column("period_key", sa.String(10), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "feature", "period_key"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_user_feature_usage_user_id", "user_feature_usage", ["user_id"])

    # ── seed: Free plan ──────────────────────────────────────────────────────
    op.bulk_insert(
        sa.table(
            "plan_feature_limits",
            sa.column("plan", sa.String),
            sa.column("feature", sa.String),
            sa.column("value", sa.Integer),
        ),
        [
            {"plan": "free", "feature": "saves_monthly",   "value": 20},
            {"plan": "free", "feature": "chat_daily",       "value": 10},
            {"plan": "free", "feature": "explore_monthly",  "value": 10},
            {"plan": "free", "feature": "video_max_sec",    "value": 600},    # 10 min
            {"plan": "free", "feature": "search",           "value": 0},
            {"plan": "free", "feature": "fork",             "value": 0},
            # Pro: saves=100/month, chat/explore=NULL(unlimited), boolean features=1
            {"plan": "pro",  "feature": "saves_monthly",   "value": 100},
            {"plan": "pro",  "feature": "chat_daily",       "value": None},
            {"plan": "pro",  "feature": "explore_monthly",  "value": None},
            {"plan": "pro",  "feature": "video_max_sec",    "value": 1200},   # 20 min
            {"plan": "pro",  "feature": "search",           "value": 1},
            {"plan": "pro",  "feature": "fork",             "value": 1},
        ],
    )


def downgrade() -> None:
    op.drop_table("user_feature_usage")
    op.drop_table("plan_feature_limits")
