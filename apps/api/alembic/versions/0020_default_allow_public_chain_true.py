"""default allow_public_chain to true for new users

Revision ID: 0020
Revises: 0019
Create Date: 2026-06-04
"""
from alembic import op

revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "users",
        "allow_public_chain",
        server_default="true",
    )


def downgrade() -> None:
    op.alter_column(
        "users",
        "allow_public_chain",
        server_default="false",
    )
