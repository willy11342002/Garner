"""add gumroad_subscription_id to subscriptions

Revision ID: 0032
Revises: 0031
Create Date: 2026-06-09
"""
import sqlalchemy as sa
from alembic import op

revision = "0032"
down_revision = "0031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "subscriptions",
        sa.Column("gumroad_subscription_id", sa.Text(), nullable=True),
    )
    op.create_index(
        "ix_subscriptions_gumroad_subscription_id",
        "subscriptions",
        ["gumroad_subscription_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_subscriptions_gumroad_subscription_id", table_name="subscriptions")
    op.drop_column("subscriptions", "gumroad_subscription_id")
