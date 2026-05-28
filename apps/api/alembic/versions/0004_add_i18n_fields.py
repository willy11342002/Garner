"""add summary_i18n and name_i18n JSONB fields

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-28

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("content_objects", sa.Column("summary_i18n", postgresql.JSONB(), nullable=True))
    op.add_column("tags", sa.Column("name_i18n", postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("tags", "name_i18n")
    op.drop_column("content_objects", "summary_i18n")
