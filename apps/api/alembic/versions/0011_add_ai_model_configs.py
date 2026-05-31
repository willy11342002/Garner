"""add_ai_model_configs

Revision ID: 0011
Revises: 0010
Create Date: 2026-05-31

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = '0011'
down_revision: Union[str, None] = '0010'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'ai_model_configs',
        sa.Column('key', sa.String(64), primary_key=True),
        sa.Column('model_id', sa.Text, nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )
    op.execute("""
        INSERT INTO ai_model_configs (key, model_id, description) VALUES
        ('llm',       'anthropic/claude-3-5-haiku',      'LLM for summarization, tagging, chat, chain analysis'),
        ('embedding', 'openai/text-embedding-3-small',   'Embedding model for semantic search (1536d — do not change without re-embedding)')
    """)


def downgrade() -> None:
    op.drop_table('ai_model_configs')
