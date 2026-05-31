"""add_transcription_source_to_content_objects

Revision ID: 0010
Revises: 0009
Create Date: 2026-05-31

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = '0010'
down_revision: Union[str, None] = '0009'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE TYPE transcription_source_enum AS ENUM ('transcript', 'whisper', 'none')")
    op.add_column('content_objects', sa.Column(
        'transcription_source',
        sa.Enum('transcript', 'whisper', 'none', name='transcription_source_enum', create_type=False),
        nullable=True,
    ))


def downgrade() -> None:
    op.drop_column('content_objects', 'transcription_source')
    op.execute("DROP TYPE transcription_source_enum")
