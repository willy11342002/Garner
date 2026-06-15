"""add_reports

Revision ID: 0045
Revises: 0044
Create Date: 2026-06-15

New table: reports
AI 產出層（報告/規劃/指南）。與知識 (user_items) 分離，不進語料、不走擷取管線。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = '0045'
down_revision: Union[str, None] = '0044'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'reports',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('title', sa.Text(), nullable=False),
        sa.Column('body_md', sa.Text(), nullable=False, server_default=''),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('source_item_ids', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('last_edited_by', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_reports_user_id', 'reports', ['user_id'])


def downgrade() -> None:
    op.drop_index('ix_reports_user_id', table_name='reports')
    op.drop_table('reports')
