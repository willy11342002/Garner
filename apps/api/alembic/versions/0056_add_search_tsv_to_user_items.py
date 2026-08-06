"""0056_add_search_tsv_to_user_items

Revision ID: 0056
Revises: 0055
Create Date: 2026-07-26

user_items 加 title_zh / notes_zh（中文斷詞後文字，當時用 CKIP，現已改為 jieba）+ search_tsv（DB 端 GENERATED
tsvector，供 hybrid search 的 BM25-like 全文檢索用），並建 GIN index。
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0056"
down_revision: Union[str, None] = "0055"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("user_items", sa.Column("title_zh", sa.Text(), nullable=True))
    op.add_column("user_items", sa.Column("notes_zh", sa.Text(), nullable=True))
    op.execute("""
        ALTER TABLE user_items ADD COLUMN search_tsv tsvector
        GENERATED ALWAYS AS (
            setweight(to_tsvector('simple', coalesce(title_zh, '')), 'A') ||
            setweight(to_tsvector('simple', coalesce(notes_zh, '')), 'B')
        ) STORED
    """)
    op.create_index(
        "ix_user_items_search_tsv",
        "user_items",
        ["search_tsv"],
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index("ix_user_items_search_tsv", table_name="user_items")
    op.execute("ALTER TABLE user_items DROP COLUMN search_tsv")
    op.drop_column("user_items", "notes_zh")
    op.drop_column("user_items", "title_zh")
