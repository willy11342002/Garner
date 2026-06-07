"""add raw_data to content_objects

Revision ID: 0023
Revises: 0022
Create Date: 2026-06-07
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision: str = "0023"
down_revision: Union[str, None] = "0022"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("content_objects", sa.Column("raw_data", JSONB, nullable=True))


def downgrade() -> None:
    op.drop_column("content_objects", "raw_data")
