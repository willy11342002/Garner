"""0049_add_trip_item_ticket_url

Revision ID: 0049
Revises: 0048
Create Date: 2026-06-17

trip_items 新增 ticket_url：票券／訂位連結（與 booked 並列，前端可點開）。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0049'
down_revision: Union[str, None] = '0048'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("trip_items", sa.Column("ticket_url", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("trip_items", "ticket_url")
