"""add extract column to user_items

Revision ID: 0041
Revises: 0040
Create Date: 2026-06-13
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0041"
down_revision = "0040"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("user_items", sa.Column("extract", JSONB, nullable=True))


def downgrade() -> None:
    op.drop_column("user_items", "extract")
