"""0043_add_pipeline_stage_columns

Revision ID: 0043
Revises: 279d5b917cf3
Create Date: 2026-06-14

Add per-stage status / duration / error columns to user_items for the
DAG pipeline: fetch → assets → [note → embedding, landmarks]
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '0043'
down_revision: Union[str, None] = '279d5b917cf3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_STAGES = ["fetch", "assets", "note", "landmarks", "embedding"]


def upgrade() -> None:
    for stage in _STAGES:
        op.add_column("user_items", sa.Column(f"{stage}_status", sa.Text(), nullable=True))
        op.add_column("user_items", sa.Column(f"{stage}_duration_ms", sa.Integer(), nullable=True))
        op.add_column("user_items", sa.Column(f"{stage}_error", sa.Text(), nullable=True))


def downgrade() -> None:
    for stage in reversed(_STAGES):
        op.drop_column("user_items", f"{stage}_error")
        op.drop_column("user_items", f"{stage}_duration_ms")
        op.drop_column("user_items", f"{stage}_status")
