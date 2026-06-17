"""0048_add_trip_item_sources

Revision ID: 0048
Revises: 5084bce132a3
Create Date: 2026-06-16

新增 trip_item_sources：TripItem ↔ 知識（user_items）多對多關聯，
讓 AI 生成行程時可依地點把卡片關聯到多則知識。
user_item_id 不設 FK（user_items 走軟刪除）。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0048'
down_revision: Union[str, None] = '5084bce132a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "trip_item_sources",
        sa.Column("trip_item_id", sa.UUID(), nullable=False),
        sa.Column("user_item_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(["trip_item_id"], ["trip_items.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("trip_item_id", "user_item_id"),
    )


def downgrade() -> None:
    op.drop_table("trip_item_sources")
