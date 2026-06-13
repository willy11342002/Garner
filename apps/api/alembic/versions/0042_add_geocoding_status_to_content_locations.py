"""0042_add_geocoding_status_to_content_locations

Revision ID: 279d5b917cf3
Revises: 0041
Create Date: 2026-06-13 23:57:15.284896

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import pgvector.sqlalchemy


revision: str = '279d5b917cf3'
down_revision: Union[str, None] = '0041'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "content_locations",
        sa.Column("geocoding_status", sa.Text(), nullable=False, server_default="done"),
    )


def downgrade() -> None:
    op.drop_column("content_locations", "geocoding_status")
