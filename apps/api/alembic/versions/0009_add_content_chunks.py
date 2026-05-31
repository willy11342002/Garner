"""add content_chunks table for chunked RAG embeddings

Revision ID: 0009
Revises: 0008
Create Date: 2026-05-31
"""
import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None

EMBEDDING_DIM = 1536


def upgrade() -> None:
    op.create_table(
        "content_chunks",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("content_id", sa.UUID(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=True),
        sa.ForeignKeyConstraint(
            ["content_id"],
            ["content_objects.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_content_chunks_content_id", "content_chunks", ["content_id"])


def downgrade() -> None:
    op.drop_index("ix_content_chunks_content_id", table_name="content_chunks")
    op.drop_table("content_chunks")
