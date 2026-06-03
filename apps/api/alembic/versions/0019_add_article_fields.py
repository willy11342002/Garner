"""add article fields

Revision ID: 0019
Revises: 0018
Create Date: 2026-06-03
"""

from alembic import op
import sqlalchemy as sa

revision = '0019'
down_revision = '0018'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('content_objects', sa.Column('content_md', sa.Text(), nullable=True))
    op.add_column('user_items', sa.Column('is_draft', sa.Boolean(), nullable=False, server_default='true'))
    op.add_column('user_items', sa.Column('is_public', sa.Boolean(), nullable=False, server_default='false'))


def downgrade() -> None:
    op.drop_column('user_items', 'is_public')
    op.drop_column('user_items', 'is_draft')
    op.drop_column('content_objects', 'content_md')
