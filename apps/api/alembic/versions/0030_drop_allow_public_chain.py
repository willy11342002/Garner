"""drop allow_public_chain column from users

Revision ID: 0030
Revises: 0029
Create Date: 2026-06-09
"""
import sqlalchemy as sa
from alembic import op

revision = "0030"
down_revision = "0029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("users", "allow_public_chain")


def downgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "allow_public_chain",
            sa.Boolean(),
            nullable=False,
            server_default="true",
        ),
    )
