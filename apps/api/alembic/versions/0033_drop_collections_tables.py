"""drop collections and collection_items tables

Revision ID: 0033
Revises: 0032
Create Date: 2026-06-10
"""
import sqlalchemy as sa
from alembic import op

revision = "0033"
down_revision = "0032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_table("collection_items")
    op.drop_table("collections")
    op.execute("DROP TYPE IF EXISTS collection_visibility_enum")


def downgrade() -> None:
    op.execute(
        """
        CREATE TYPE collection_visibility_enum AS ENUM ('private', 'link', 'public')
        """
    )
    op.create_table(
        "collections",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("source_tag_id", sa.UUID(), nullable=True),
        sa.Column("fork_from_collection_id", sa.UUID(), nullable=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column(
            "visibility",
            sa.Enum("private", "link", "public", name="collection_visibility_enum"),
            nullable=False,
        ),
        sa.Column("slug", sa.Text(), nullable=False),
        sa.Column("fork_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["fork_from_collection_id"], ["collections.id"]),
        sa.ForeignKeyConstraint(["source_tag_id"], ["tags.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_table(
        "collection_items",
        sa.Column("collection_id", sa.UUID(), nullable=False),
        sa.Column("content_id", sa.UUID(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=True),
        sa.Column("added_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["collection_id"], ["collections.id"]),
        sa.ForeignKeyConstraint(["content_id"], ["content_objects.id"]),
        sa.PrimaryKeyConstraint("collection_id", "content_id"),
    )
