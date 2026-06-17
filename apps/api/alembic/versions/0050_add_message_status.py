"""0050_add_message_status

Revision ID: 0050
Revises: 0049
Create Date: 2026-06-17

chat_messages 新增 status 欄位，支援斷線重連流程。
existing rows 視為已完成（complete）；新的 assistant placeholder 從 pending 開始。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0050'
down_revision: Union[str, None] = '0049'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "chat_messages",
        sa.Column("status", sa.Text(), nullable=False, server_default="complete"),
    )


def downgrade() -> None:
    op.drop_column("chat_messages", "status")
