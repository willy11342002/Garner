"""migrate_chat_quota_to_monthly

Revision ID: 7fffbb148406
Revises: 0035
Create Date: 2026-06-10 17:48:19.751406

- Rename plan_feature_limits feature 'chat_daily' → 'chat_monthly'
- Set free plan chat_monthly limit = 150
- Set pro plan chat_monthly limit = 600
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import pgvector.sqlalchemy


revision: str = '7fffbb148406'
down_revision: Union[str, None] = '0035'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Rename feature key: chat_daily → chat_monthly
    op.execute("""
        UPDATE plan_feature_limits
        SET feature = 'chat_monthly'
        WHERE feature = 'chat_daily'
    """)

    # Set free plan limit to 150
    op.execute("""
        UPDATE plan_feature_limits pfl
        SET value = 150
        FROM plans p
        WHERE pfl.plan_id = p.id
          AND p.name = 'free'
          AND pfl.feature = 'chat_monthly'
    """)

    # Set pro plan limit to 600
    op.execute("""
        UPDATE plan_feature_limits pfl
        SET value = 600
        FROM plans p
        WHERE pfl.plan_id = p.id
          AND p.name = 'pro'
          AND pfl.feature = 'chat_monthly'
    """)


def downgrade() -> None:
    # Restore free plan limit to 10 (original daily value)
    op.execute("""
        UPDATE plan_feature_limits pfl
        SET value = 10
        FROM plans p
        WHERE pfl.plan_id = p.id
          AND p.name = 'free'
          AND pfl.feature = 'chat_monthly'
    """)

    # Restore pro plan limit to NULL (original unlimited)
    op.execute("""
        UPDATE plan_feature_limits pfl
        SET value = NULL
        FROM plans p
        WHERE pfl.plan_id = p.id
          AND p.name = 'pro'
          AND pfl.feature = 'chat_monthly'
    """)

    # Rename feature key back: chat_monthly → chat_daily
    op.execute("""
        UPDATE plan_feature_limits
        SET feature = 'chat_daily'
        WHERE feature = 'chat_monthly'
    """)
