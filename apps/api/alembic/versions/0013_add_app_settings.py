"""add app_settings table

Revision ID: 0013
Revises: 0012
Create Date: 2026-05-31
"""
from alembic import op
import sqlalchemy as sa

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "app_settings",
        sa.Column("key", sa.String(64), primary_key=True),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.execute(
        """
        INSERT INTO app_settings (key, value, description) VALUES
        ('chain_distance_cutoff', '0.45', 'Chain 探索候選的 cosine distance 門檻（越大越寬鬆，0~1）')
        """
    )


def downgrade() -> None:
    op.drop_table("app_settings")
