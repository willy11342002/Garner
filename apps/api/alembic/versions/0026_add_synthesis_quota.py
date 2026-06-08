"""add synthesis_monthly quota to plan_feature_limits

Revision ID: 0026
Revises: 0025
Create Date: 2026-06-07
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0026"
down_revision: Union[str, None] = "0025"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        INSERT INTO plan_feature_limits (plan_id, feature, value)
        SELECT p.id, 'synthesis_monthly', 10
        FROM plans p
        WHERE p.name = 'free'
        ON CONFLICT (plan_id, feature) DO NOTHING
    """)
    op.execute("""
        INSERT INTO plan_feature_limits (plan_id, feature, value)
        SELECT p.id, 'synthesis_monthly', 100
        FROM plans p
        WHERE p.name = 'pro'
        ON CONFLICT (plan_id, feature) DO NOTHING
    """)


def downgrade() -> None:
    op.execute("""
        DELETE FROM plan_feature_limits
        WHERE feature = 'synthesis_monthly'
    """)
