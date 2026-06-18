"""Add tiktok to source_type_enum"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0051'
down_revision = '0050'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add 'tiktok' value to source_type_enum
    op.execute("ALTER TYPE source_type_enum ADD VALUE 'tiktok'")


def downgrade() -> None:
    # PostgreSQL doesn't support removing enum values, so we need to recreate the enum
    # This is a limitation of PostgreSQL enums
    op.execute("ALTER TYPE source_type_enum RENAME TO source_type_enum_old")
    op.execute("CREATE TYPE source_type_enum AS ENUM ('youtube', 'article', 'ig', 'note')")
    op.execute(
        "ALTER TABLE user_items ALTER COLUMN source_type TYPE source_type_enum "
        "USING source_type::text::source_type_enum"
    )
    op.execute("DROP TYPE source_type_enum_old")
