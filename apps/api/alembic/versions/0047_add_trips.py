"""0047_add_trips

Revision ID: 5084bce132a3
Revises: 0046
Create Date: 2026-06-16 09:43:50.012978

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import pgvector.sqlalchemy


revision: str = '5084bce132a3'
down_revision: Union[str, None] = '0046'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── trips ─────────────────────────────────────────────────────────────────
    op.create_table(
        "trips",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("source_item_ids", sa.dialects.postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("last_edited_by", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_trips_user_id", "trips", ["user_id"])

    # ── trip_items ────────────────────────────────────────────────────────────
    op.create_table(
        "trip_items",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("trip_id", sa.UUID(), nullable=False),
        sa.Column("user_item_id", sa.UUID(), nullable=True),
        sa.Column("kind", sa.Text(), nullable=False, server_default="event"),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("emoji", sa.Text(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("category", sa.Text(), nullable=True),
        sa.Column("booked", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("start_time", sa.Time(), nullable=True),
        sa.Column("end_time", sa.Time(), nullable=True),
        sa.Column("order_index", sa.Float(), nullable=False, server_default="0"),
        sa.Column("place_name", sa.Text(), nullable=True),
        sa.Column("lat", sa.Float(), nullable=True),
        sa.Column("lng", sa.Float(), nullable=True),
        sa.Column("geocoding_status", sa.Text(), nullable=False, server_default="done"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["trip_id"], ["trips.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_trip_items_trip_id", "trip_items", ["trip_id"])
    op.create_index("ix_trip_items_trip_id_order", "trip_items", ["trip_id", "order_index"])

    # ── trip_tags ─────────────────────────────────────────────────────────────
    op.create_table(
        "trip_tags",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("color", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "name", name="uq_trip_tags_user_name"),
    )
    op.create_index("ix_trip_tags_user_id", "trip_tags", ["user_id"])

    # ── trip_item_tags ────────────────────────────────────────────────────────
    op.create_table(
        "trip_item_tags",
        sa.Column("trip_item_id", sa.UUID(), nullable=False),
        sa.Column("trip_tag_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(["trip_item_id"], ["trip_items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["trip_tag_id"], ["trip_tags.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("trip_item_id", "trip_tag_id"),
    )


def downgrade() -> None:
    op.drop_table("trip_item_tags")
    op.drop_index("ix_trip_tags_user_id", table_name="trip_tags")
    op.drop_table("trip_tags")
    op.drop_index("ix_trip_items_trip_id_order", table_name="trip_items")
    op.drop_index("ix_trip_items_trip_id", table_name="trip_items")
    op.drop_table("trip_items")
    op.drop_index("ix_trips_user_id", table_name="trips")
    op.drop_table("trips")
