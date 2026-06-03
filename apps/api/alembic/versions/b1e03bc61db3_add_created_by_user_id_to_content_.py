"""add_created_by_user_id_to_content_objects

Revision ID: b1e03bc61db3
Revises: 0016
Create Date: 2026-06-03 14:19:20.572616

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'b1e03bc61db3'
down_revision: Union[str, None] = '0016'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('content_objects', sa.Column('created_by_user_id', sa.Uuid(), nullable=True))
    op.create_index('ix_content_objects_created_by_user_id', 'content_objects', ['created_by_user_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_content_objects_created_by_user_id', table_name='content_objects')
    op.drop_column('content_objects', 'created_by_user_id')
