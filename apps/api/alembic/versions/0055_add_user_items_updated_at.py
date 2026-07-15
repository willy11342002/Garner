"""Add updated_at to user_items for ingest pipeline stall detection"""
import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = '0055'
down_revision = '0054'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user_items",
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("user_items", "updated_at")
