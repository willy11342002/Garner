"""add confirmed column to item_tags

Revision ID: 0005
Revises: 0004
Create Date: 2026-05-28

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "item_tags",
        sa.Column("confirmed", sa.Boolean(), nullable=False, server_default="true"),
    )
    # Existing AI-generated tags start as confirmed (no review backlog for old data)
    op.execute("UPDATE item_tags SET confirmed = true WHERE source = 'ai'")


def downgrade() -> None:
    op.drop_column("item_tags", "confirmed")
