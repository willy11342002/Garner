"""0044_backfill_pipeline_stage_complete

Revision ID: 0044
Revises: 0043
Create Date: 2026-06-14

Backfill pipeline stage status columns to "complete" for all existing
user_items that have already been processed (parsed_at IS NOT NULL).
Rows still pending (parsed_at IS NULL) are left NULL so the new pipeline
picks them up correctly.
"""
from typing import Sequence, Union

from alembic import op

revision: str = '0044'
down_revision: Union[str, None] = '0043'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_STAGES = ["fetch", "assets", "note", "landmarks", "embedding"]


def upgrade() -> None:
    status_sets = ", ".join(f"{s}_status = 'complete'" for s in _STAGES)
    op.execute(f"""
        UPDATE user_items
        SET {status_sets}
        WHERE parsed_at IS NOT NULL
          AND deleted_at IS NULL
    """)


def downgrade() -> None:
    status_nulls = ", ".join(f"{s}_status = NULL" for s in _STAGES)
    op.execute(f"UPDATE user_items SET {status_nulls}")
