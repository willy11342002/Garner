"""drop content_objects, move embedding/chunks/locations to user_items

Revision ID: 0040
Revises: 0039
Create Date: 2026-06-12
"""

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import JSONB

revision = "0040"
down_revision = "0039"
branch_labels = None
depends_on = None

EMBEDDING_DIM = 1536


def upgrade() -> None:
    # ── 1. user_items: add new columns ───────────────────────────────────────
    op.add_column("user_items", sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=True))
    op.add_column("user_items", sa.Column("raw_data", JSONB, nullable=True))
    op.add_column("user_items", sa.Column("duration_sec", sa.Integer, nullable=True))

    # ── 2. Copy data from content_objects → user_items ───────────────────────
    op.execute("""
        UPDATE user_items ui
        SET
            embedding    = co.embedding,
            raw_data     = co.raw_data,
            duration_sec = co.duration_sec
        FROM content_objects co
        WHERE ui.content_id = co.id
    """)

    # ── 3. content_chunks: add user_item_id, fan-out, drop content_id ────────
    op.add_column("content_chunks", sa.Column("user_item_id", sa.UUID, nullable=True))

    # Assign existing chunks to the earliest user_item per content
    op.execute("""
        WITH ranked AS (
            SELECT ui.id AS ui_id,
                   ui.content_id,
                   ROW_NUMBER() OVER (
                       PARTITION BY ui.content_id ORDER BY ui.saved_at
                   ) AS rn
            FROM user_items ui
        )
        UPDATE content_chunks cc
        SET user_item_id = ranked.ui_id
        FROM ranked
        WHERE ranked.content_id = cc.content_id
          AND ranked.rn = 1
    """)

    # Fan-out: insert duplicate chunks for any additional user_items sharing same content
    op.execute("""
        INSERT INTO content_chunks (id, user_item_id, chunk_index, text, embedding)
        SELECT gen_random_uuid(), ui.id, cc.chunk_index, cc.text, cc.embedding
        FROM content_chunks cc
        JOIN user_items ui ON ui.content_id = cc.content_id
        WHERE ui.id <> cc.user_item_id
          AND cc.user_item_id IS NOT NULL
    """)

    # Delete orphaned chunks (content_objects with no user_items)
    op.execute("DELETE FROM content_chunks WHERE user_item_id IS NULL")

    op.alter_column("content_chunks", "user_item_id", nullable=False)
    op.create_foreign_key(
        "fk_content_chunks_user_item_id",
        "content_chunks", "user_items",
        ["user_item_id"], ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_content_chunks_user_item_id", "content_chunks", ["user_item_id"])
    op.drop_index("ix_content_chunks_content_id", table_name="content_chunks")
    op.drop_constraint("content_chunks_content_id_fkey", "content_chunks", type_="foreignkey")
    op.drop_column("content_chunks", "content_id")

    # ── 4. content_locations: add user_item_id, fan-out, drop content_id ─────
    op.add_column("content_locations", sa.Column("user_item_id", sa.UUID, nullable=True))

    op.execute("""
        WITH ranked AS (
            SELECT ui.id AS ui_id,
                   ui.content_id,
                   ROW_NUMBER() OVER (
                       PARTITION BY ui.content_id ORDER BY ui.saved_at
                   ) AS rn
            FROM user_items ui
        )
        UPDATE content_locations cl
        SET user_item_id = ranked.ui_id
        FROM ranked
        WHERE ranked.content_id = cl.content_id
          AND ranked.rn = 1
    """)

    op.execute("""
        INSERT INTO content_locations (id, user_item_id, name, lat, lng, source, order_index, created_at)
        SELECT gen_random_uuid(), ui.id, cl.name, cl.lat, cl.lng, cl.source, cl.order_index, cl.created_at
        FROM content_locations cl
        JOIN user_items ui ON ui.content_id = cl.content_id
        WHERE ui.id <> cl.user_item_id
          AND cl.user_item_id IS NOT NULL
    """)

    # Orphaned locations (content with no user_items) are dropped via cascade below.
    # Delete them explicitly before NOT NULL constraint.
    op.execute("DELETE FROM content_locations WHERE user_item_id IS NULL")

    op.alter_column("content_locations", "user_item_id", nullable=False)
    op.create_foreign_key(
        "fk_content_locations_user_item_id",
        "content_locations", "user_items",
        ["user_item_id"], ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_content_locations_user_item_id", "content_locations", ["user_item_id"])
    op.drop_constraint("content_locations_content_id_fkey", "content_locations", type_="foreignkey")
    op.drop_column("content_locations", "content_id")

    # ── 5. user_items: make url NOT NULL, add unique(user_id, url) ───────────
    op.execute("UPDATE user_items SET url = '' WHERE url IS NULL")
    op.alter_column("user_items", "url", nullable=False)
    op.create_unique_constraint("uq_user_items_user_id_url", "user_items", ["user_id", "url"])

    # ── 6. user_items: drop content_id FK and column ─────────────────────────
    op.drop_constraint("user_items_content_id_fkey", "user_items", type_="foreignkey")
    op.drop_index("ix_user_items_content_id", table_name="user_items")
    op.drop_column("user_items", "content_id")

    # ── 7. Drop content_objects (no more dependents) ──────────────────────────
    op.drop_table("content_objects")
    # source_type_enum is still used by user_items.source_type — keep it


def downgrade() -> None:
    raise NotImplementedError("Downgrade not supported: content_objects data is gone")
