"""add_place_cache

Revision ID: 0038
Revises: 0037
Create Date: 2026-06-11

New table: place_cache
Caches Google Places API results (name, rating, reviews, photos, etc.) by place_id.
TTL-based invalidation is handled at the application layer (7 days).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0038'
down_revision: Union[str, None] = '0037'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'place_cache',
        sa.Column('place_id', sa.Text(), nullable=False),
        sa.Column('name', sa.Text(), nullable=True),
        sa.Column('rating', sa.Float(), nullable=True),
        sa.Column('reviews', sa.JSON(), nullable=True),
        sa.Column('photos', sa.JSON(), nullable=True),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('phone', sa.Text(), nullable=True),
        sa.Column('opening_hours', sa.JSON(), nullable=True),
        sa.Column('maps_url', sa.Text(), nullable=True),
        sa.Column('cached_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('place_id'),
    )


def downgrade() -> None:
    op.drop_table('place_cache')
