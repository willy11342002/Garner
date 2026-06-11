"""remove confirmed columns from item_tags and content_locations

Revision ID: 0039
Revises: 0038
Create Date: 2026-06-11

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0039"
down_revision: Union[str, None] = "0038"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("item_tags", "confirmed")
    op.drop_column("content_locations", "confirmed")


def downgrade() -> None:
    op.add_column(
        "item_tags",
        sa.Column("confirmed", sa.Boolean(), nullable=False, server_default="true"),
    )
    op.add_column(
        "content_locations",
        sa.Column("confirmed", sa.Boolean(), nullable=False, server_default="false"),
    )
