"""0054_add_embedding_to_reports_trips

Revision ID: 0054
Revises: 0053
Create Date: 2026-07-08

reports 和 trips 各加 embedding vector(1536)，供 search_reports / search_trips chat tool 語意查詢。
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "0054"
down_revision: Union[str, None] = "0053"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("reports", sa.Column("embedding", Vector(1536), nullable=True))
    op.add_column("trips", sa.Column("embedding", Vector(1536), nullable=True))
    op.create_index(
        "ix_reports_embedding",
        "reports",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_with={"m": 16, "ef_construction": 64},
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )
    op.create_index(
        "ix_trips_embedding",
        "trips",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_with={"m": 16, "ef_construction": 64},
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )


def downgrade() -> None:
    op.drop_index("ix_reports_embedding", table_name="reports")
    op.drop_index("ix_trips_embedding", table_name="trips")
    op.drop_column("reports", "embedding")
    op.drop_column("trips", "embedding")
