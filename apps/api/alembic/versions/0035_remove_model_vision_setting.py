"""remove_model_vision_setting

Revision ID: 0035
Revises: 0034
Create Date: 2026-06-10

"""
from typing import Sequence, Union

from alembic import op

revision: str = '0035'
down_revision: Union[str, None] = '0034'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("DELETE FROM app_settings WHERE key = 'model.vision'")


def downgrade() -> None:
    op.execute("""
        INSERT INTO app_settings (key, value, description) VALUES
        ('model.vision', 'anthropic/claude-3-haiku', 'Vision model for image description (must support multimodal input)')
        ON CONFLICT (key) DO NOTHING
    """)
