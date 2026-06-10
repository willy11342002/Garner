"""seed_vision_video_model_configs

Migrate ai_model_configs into app_settings (key prefix: model.*),
seed vision and video_llm entries, then drop the ai_model_configs table.

Revision ID: 0034
Revises: 0033
Create Date: 2026-06-10

"""
from typing import Sequence, Union

from alembic import op

revision: str = '0034'
down_revision: Union[str, None] = '0033'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Migrate existing rows from ai_model_configs → app_settings
    op.execute("""
        INSERT INTO app_settings (key, value, description)
        SELECT 'model.' || key, model_id, description
        FROM ai_model_configs
        ON CONFLICT (key) DO NOTHING
    """)

    # Seed video_llm (not present in old table)
    op.execute("""
        INSERT INTO app_settings (key, value, description) VALUES
        ('model.video_llm', 'google/gemini-2.5-flash', 'Video LLM for native video_url analysis')
        ON CONFLICT (key) DO NOTHING
    """)

    op.drop_table('ai_model_configs')


def downgrade() -> None:
    import sqlalchemy as sa
    op.create_table(
        'ai_model_configs',
        sa.Column('key', sa.String(64), primary_key=True),
        sa.Column('model_id', sa.Text, nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )
    op.execute("""
        INSERT INTO ai_model_configs (key, model_id, description)
        SELECT substring(key FROM 7), value, description
        FROM app_settings
        WHERE key LIKE 'model.%'
    """)
    op.execute("DELETE FROM app_settings WHERE key LIKE 'model.%'")
