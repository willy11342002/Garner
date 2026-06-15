"""0046_drop_reports_deleted_at

Revision ID: 0046
Revises: 0045
Create Date: 2026-06-15

報告改為直接硬刪除，移除 reports.deleted_at（軟刪除）欄位。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0046'
down_revision: Union[str, None] = '0045'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column('reports', 'deleted_at')


def downgrade() -> None:
    op.add_column('reports', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
