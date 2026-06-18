"""Add facebook_reel and facebook_post to source_type_enum"""
from alembic import op


# revision identifiers, used by Alembic.
revision = '0052'
down_revision = '0051'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE source_type_enum ADD VALUE 'facebook_reel'")
    op.execute("ALTER TYPE source_type_enum ADD VALUE 'facebook_post'")


def downgrade() -> None:
    # PostgreSQL doesn't support removing enum values; recreate without the two new values
    op.execute("ALTER TYPE source_type_enum RENAME TO source_type_enum_old")
    op.execute("CREATE TYPE source_type_enum AS ENUM ('youtube', 'article', 'ig', 'tiktok', 'note')")
    op.execute(
        "ALTER TABLE user_items ALTER COLUMN source_type TYPE source_type_enum "
        "USING source_type::text::source_type_enum"
    )
    op.execute("DROP TYPE source_type_enum_old")
