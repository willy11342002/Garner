"""add_whisper_quota

Revision ID: f5cf11e62369
Revises: 0001
Create Date: 2026-05-28 10:55:57.785375

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import pgvector.sqlalchemy


revision: str = '0002'
down_revision: Union[str, None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'whisper_usage',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('used_seconds', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_whisper_usage_date'), 'whisper_usage', ['date'], unique=False)
    op.create_index(op.f('ix_whisper_usage_user_id'), 'whisper_usage', ['user_id'], unique=False)
    op.add_column('plans', sa.Column('whisper_daily_limit_seconds', sa.Integer(), nullable=False, server_default='3600'))


def downgrade() -> None:
    op.drop_column('plans', 'whisper_daily_limit_seconds')
    op.drop_index(op.f('ix_whisper_usage_user_id'), table_name='whisper_usage')
    op.drop_index(op.f('ix_whisper_usage_date'), table_name='whisper_usage')
    op.drop_table('whisper_usage')
