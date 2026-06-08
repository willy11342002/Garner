"""drop is_draft and transcription_source fields

Revision ID: 0028
Revises: 0027
Create Date: 2026-06-08

異動說明：
- user_items 移除 is_draft（publish 功能下架，草稿狀態不再有意義）
- user_items 移除 transcription_source（前端未使用，snapshot 無需保留）
- content_objects 移除 transcription_source（provider 端無任何讀取邏輯）
- 保留 transcription_source_enum type 不刪（避免影響 0010 migration chain）
"""

from alembic import op
import sqlalchemy as sa


revision = "0028"
down_revision = "0027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("user_items", "is_draft")
    op.drop_column("user_items", "transcription_source")
    op.drop_column("content_objects", "transcription_source")


def downgrade() -> None:
    op.add_column(
        "content_objects",
        sa.Column(
            "transcription_source",
            sa.Enum("transcript", "whisper", "none", name="transcription_source_enum", create_type=False),
            nullable=True,
        ),
    )
    op.add_column(
        "user_items",
        sa.Column(
            "transcription_source",
            sa.Enum("transcript", "whisper", "none", name="transcription_source_enum", create_type=False),
            nullable=True,
        ),
    )
    op.add_column(
        "user_items",
        sa.Column("is_draft", sa.Boolean(), nullable=False, server_default="true"),
    )
