"""add notifications table

Revision ID: 0014
Revises: 0013
Create Date: 2026-06-01
"""
from alembic import op

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE notification_type_enum AS ENUM ('item_processed', 'item_failed', 'system');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id),
            type notification_type_enum NOT NULL,
            title VARCHAR(255) NOT NULL,
            body TEXT,
            is_read BOOLEAN NOT NULL DEFAULT false,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_notifications_user_id ON notifications (user_id)")


def downgrade():
    op.execute("DROP INDEX IF EXISTS ix_notifications_user_id")
    op.execute("DROP TABLE IF EXISTS notifications")
    op.execute("DROP TYPE IF EXISTS notification_type_enum")
