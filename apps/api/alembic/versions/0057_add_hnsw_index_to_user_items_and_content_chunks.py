"""0057_add_hnsw_index_to_user_items_and_content_chunks

Revision ID: 0057
Revises: 0056
Create Date: 2026-07-27

user_items.embedding 和 content_chunks.embedding 至今沒有 ANN index（全表 seq scan），
跟 reports/trips（0054）、tags（0018）的 embedding 不一致，這裡補上同樣的 HNSW index。
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0057"
down_revision: Union[str, None] = "0056"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_user_items_embedding",
        "user_items",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_with={"m": 16, "ef_construction": 64},
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )
    op.create_index(
        "ix_content_chunks_embedding",
        "content_chunks",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_with={"m": 16, "ef_construction": 64},
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )


def downgrade() -> None:
    op.drop_index("ix_content_chunks_embedding", table_name="content_chunks")
    op.drop_index("ix_user_items_embedding", table_name="user_items")
