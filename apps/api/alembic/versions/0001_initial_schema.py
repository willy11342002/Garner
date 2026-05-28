"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-05-27

"""
from typing import Sequence, Union

import pgvector.sqlalchemy
import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "users",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("email", sa.Text(), nullable=True),
        sa.Column("username", sa.String(100), nullable=False),
        sa.Column("monthly_saves", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "sso_provider",
            sa.Enum("google", "github", "apple", name="sso_provider_enum"),
            nullable=True,
        ),
        sa.Column("sso_subject", sa.Text(), nullable=True),
        sa.Column("password_hash", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sso_subject"),
    )

    op.create_table(
        "plans",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("price_monthly", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_saves_per_month", sa.Integer(), nullable=True),
        sa.Column("max_storage_mb", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "subscriptions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("plan_id", sa.UUID(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("trialing", "active", "cancelled", "expired", name="subscription_status_enum"),
            nullable=False,
        ),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["plan_id"], ["plans.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_subscriptions_user_id", "subscriptions", ["user_id"])
    op.create_index("ix_subscriptions_plan_id", "subscriptions", ["plan_id"])

    op.create_table(
        "content_objects",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column(
            "source_type",
            sa.Enum("youtube", "article", "ig", name="source_type_enum"),
            nullable=False,
        ),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("thumbnail_url", sa.Text(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("embedding", pgvector.sqlalchemy.Vector(1536), nullable=True),
        sa.Column("duration_sec", sa.Integer(), nullable=True),
        sa.Column("parsed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("url"),
    )
    op.execute(
        "CREATE INDEX ix_content_objects_embedding ON content_objects "
        "USING hnsw (embedding vector_cosine_ops)"
    )

    op.create_table(
        "tags",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("color", sa.String(7), nullable=True),
        sa.Column("item_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tags_user_id", "tags", ["user_id"])

    op.create_table(
        "user_items",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("content_id", sa.UUID(), nullable=False),
        sa.Column("fork_from_item_id", sa.UUID(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("active", "archived", "deleted", name="user_item_status_enum"),
            nullable=False,
            server_default="active",
        ),
        sa.Column(
            "saved_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("last_opened_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["content_id"], ["content_objects.id"]),
        sa.ForeignKeyConstraint(["fork_from_item_id"], ["user_items.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_items_user_id", "user_items", ["user_id"])
    op.create_index("ix_user_items_content_id", "user_items", ["content_id"])

    op.create_table(
        "item_tags",
        sa.Column("user_item_id", sa.UUID(), nullable=False),
        sa.Column("tag_id", sa.UUID(), nullable=False),
        sa.Column(
            "source",
            sa.Enum("ai", "user", name="tag_source_enum"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_item_id"], ["user_items.id"]),
        sa.ForeignKeyConstraint(["tag_id"], ["tags.id"]),
        sa.PrimaryKeyConstraint("user_item_id", "tag_id"),
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
            server_default="private",
        ),
        sa.Column("slug", sa.Text(), nullable=False),
        sa.Column("fork_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["source_tag_id"], ["tags.id"]),
        sa.ForeignKeyConstraint(["fork_from_collection_id"], ["collections.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_collections_user_id", "collections", ["user_id"])

    op.create_table(
        "collection_items",
        sa.Column("collection_id", sa.UUID(), nullable=False),
        sa.Column("content_id", sa.UUID(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "added_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["collection_id"], ["collections.id"]),
        sa.ForeignKeyConstraint(["content_id"], ["content_objects.id"]),
        sa.PrimaryKeyConstraint("collection_id", "content_id"),
    )


def downgrade() -> None:
    op.drop_table("collection_items")
    op.drop_table("collections")
    op.drop_table("item_tags")
    op.drop_table("user_items")
    op.drop_table("tags")
    op.drop_table("content_objects")
    op.drop_table("subscriptions")
    op.drop_table("plans")
    op.drop_table("users")
    op.execute("DROP TYPE IF EXISTS collection_visibility_enum")
    op.execute("DROP TYPE IF EXISTS tag_source_enum")
    op.execute("DROP TYPE IF EXISTS user_item_status_enum")
    op.execute("DROP TYPE IF EXISTS source_type_enum")
    op.execute("DROP TYPE IF EXISTS subscription_status_enum")
    op.execute("DROP TYPE IF EXISTS sso_provider_enum")
