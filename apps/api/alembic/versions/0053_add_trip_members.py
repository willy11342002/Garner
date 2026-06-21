"""0053_add_trip_members

Revision ID: 0053
Revises: 0052
Create Date: 2026-06-21

trip 共用功能：
- 新增 trip_members 表（editor / viewer 成員）
- trips 加 invite_token、invite_role（邀請連結）
- notifications 加 trip_id（trip_invited 通知）
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0053'
down_revision: Union[str, None] = '0052'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE notification_type_enum ADD VALUE IF NOT EXISTS 'trip_invited'")

    op.create_table(
        "trip_members",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("trip_id", sa.UUID(), nullable=False),
        sa.Column("member_user_id", sa.UUID(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False, server_default="viewer"),
        sa.Column("invited_by", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["trip_id"], ["trips.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["member_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["invited_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("trip_id", "member_user_id", name="uq_trip_members_trip_user"),
    )
    op.create_index("ix_trip_members_trip_id", "trip_members", ["trip_id"])
    op.create_index("ix_trip_members_member_user_id", "trip_members", ["member_user_id"])

    op.add_column("trips", sa.Column("invite_token", sa.UUID(), nullable=True))
    op.create_unique_constraint("uq_trips_invite_token", "trips", ["invite_token"])
    op.add_column("trips", sa.Column("invite_role", sa.Text(), nullable=False, server_default="viewer"))

    op.add_column("notifications", sa.Column("trip_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "fk_notifications_trip_id",
        "notifications", "trips",
        ["trip_id"], ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_notifications_trip_id", "notifications", type_="foreignkey")
    op.drop_column("notifications", "trip_id")

    op.drop_constraint("uq_trips_invite_token", "trips", type_="unique")
    op.drop_column("trips", "invite_role")
    op.drop_column("trips", "invite_token")

    op.drop_index("ix_trip_members_member_user_id", table_name="trip_members")
    op.drop_index("ix_trip_members_trip_id", table_name="trip_members")
    op.drop_table("trip_members")
