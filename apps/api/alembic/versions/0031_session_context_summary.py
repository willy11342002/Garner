"""migrate memory_summary from users to chat_sessions.context_summary

Revision ID: 0031
Revises: 0030
Create Date: 2026-06-09
"""
import sqlalchemy as sa
from alembic import op

revision = "0031"
down_revision = "0030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("chat_sessions", sa.Column("context_summary", sa.Text(), nullable=True))
    op.drop_column("users", "memory_summary")


def downgrade() -> None:
    op.drop_column("chat_sessions", "context_summary")
    op.add_column("users", sa.Column("memory_summary", sa.Text(), nullable=True))
