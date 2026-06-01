"""add item_id to notifications

Revision ID: 0015
Revises: 0014
Create Date: 2026-06-01
"""
from alembic import op
import sqlalchemy as sa

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "notifications",
        sa.Column("item_id", sa.UUID(), sa.ForeignKey("user_items.id"), nullable=True),
    )


def downgrade():
    op.drop_column("notifications", "item_id")
