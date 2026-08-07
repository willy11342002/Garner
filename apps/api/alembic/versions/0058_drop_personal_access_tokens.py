"""0058_drop_personal_access_tokens

Revision ID: 0058
Revises: 0057
Create Date: 2026-08-07

PAT（personal access token）原本只有兩個用途：Chrome Extension 與 iOS 捷徑帶 Bearer
呼叫 API。兩者都已改成「開分頁到 /app/quick-add?url=...」由網頁版用既有 Supabase
session 完成存入，不再需要長期有效的 token，整套 PAT 機制隨之下架。

表內既有的 token 在 app 端已無驗證路徑（dependencies.get_current_user 只剩 JWT），
留著只是一堆失效的憑證雜湊，這裡直接把表刪掉。downgrade 只還原結構，不還原資料。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0058"
down_revision: Union[str, None] = "0057"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index("ix_pat_token_hash", table_name="personal_access_tokens")
    op.drop_index("ix_pat_user_id", table_name="personal_access_tokens")
    op.drop_table("personal_access_tokens")


def downgrade() -> None:
    op.create_table(
        "personal_access_tokens",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("token_hash", sa.Text(), nullable=False),
        sa.Column("last_used_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("revoked_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_pat_user_id", "personal_access_tokens", ["user_id"])
    op.create_index("ix_pat_token_hash", "personal_access_tokens", ["token_hash"])
