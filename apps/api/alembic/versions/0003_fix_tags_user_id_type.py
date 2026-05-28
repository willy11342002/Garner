"""fix tags.user_id type from varchar to uuid

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-28

"""
from typing import Sequence, Union

from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE tags ALTER COLUMN user_id TYPE uuid USING user_id::uuid")
    op.create_foreign_key("tags_user_id_fkey", "tags", "users", ["user_id"], ["id"])


def downgrade() -> None:
    op.drop_constraint("tags_user_id_fkey", "tags", type_="foreignkey")
    op.execute("ALTER TABLE tags ALTER COLUMN user_id TYPE varchar(36) USING user_id::varchar")
