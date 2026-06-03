"""add tag embedding

Revision ID: 0017
Revises: 0016
Create Date: 2026-06-03
"""
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("tags", sa.Column("embedding", Vector(1536), nullable=True))
    op.create_index(
        "ix_tags_embedding",
        "tags",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_with={"m": 16, "ef_construction": 64},
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )


def downgrade():
    op.drop_index("ix_tags_embedding", table_name="tags")
    op.drop_column("tags", "embedding")
