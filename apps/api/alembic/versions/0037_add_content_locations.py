"""add_content_locations

Revision ID: 0037
Revises: 7fffbb148406
Create Date: 2026-06-11

New table: content_locations
Stores landmark data extracted from IG metadata and AI analysis.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0037'
down_revision: Union[str, None] = '7fffbb148406'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'content_locations',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('content_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('lat', sa.Float(), nullable=True),
        sa.Column('lng', sa.Float(), nullable=True),
        sa.Column('source', sa.Text(), nullable=False),
        sa.Column('confirmed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('order_index', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['content_id'], ['content_objects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_content_locations_content_id', 'content_locations', ['content_id'])
    op.create_index('ix_content_locations_lat_lng', 'content_locations', ['lat', 'lng'])


def downgrade() -> None:
    op.drop_index('ix_content_locations_lat_lng', table_name='content_locations')
    op.drop_index('ix_content_locations_content_id', table_name='content_locations')
    op.drop_table('content_locations')
