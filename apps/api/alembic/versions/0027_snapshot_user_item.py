"""snapshot display fields onto user_items; move content_md & ownership to user_items

Revision ID: 0027
Revises: 0026
Create Date: 2026-06-08

異動說明：
- user_items 新增 snapshot 欄位（title/summary/thumbnail_url 等），讀取 UserItem 不再需要 JOIN content_objects
- source_type enum 新增 'note'（使用者手寫文章，原本靠 created_by_user_id 辨別）
- content_md 從 content_objects 移至 user_items（只屬於使用者，非共享內容）
- created_by_user_id 從 content_objects 移除（由 user_items.source_type='note' 取代）
- content_objects 保留 title/summary/thumbnail_url 供 CollectionItem 繼續使用
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0027"
down_revision = "0026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. 新增 'note' 到 source_type enum ───────────────────────────────────
    # PostgreSQL 限制：ALTER TYPE ADD VALUE 新增的值不能在同一 transaction 內使用。
    # 用 COMMIT / BEGIN 把它夾在獨立的 transaction 裡，讓 'note' 先落地。
    op.execute(sa.text("COMMIT"))
    op.execute(sa.text("ALTER TYPE source_type_enum ADD VALUE IF NOT EXISTS 'note'"))
    op.execute(sa.text("BEGIN"))

    # ── 2. user_items 加入 snapshot 欄位 ──────────────────────────────────────
    op.add_column("user_items", sa.Column("url", sa.Text(), nullable=True))
    op.add_column("user_items", sa.Column("title", sa.Text(), nullable=True))
    op.add_column("user_items", sa.Column("summary", sa.Text(), nullable=True))
    op.add_column("user_items", sa.Column("summary_i18n", postgresql.JSONB(), nullable=True))
    op.add_column("user_items", sa.Column("thumbnail_url", sa.Text(), nullable=True))
    op.add_column(
        "user_items",
        sa.Column(
            "source_type",
            sa.Enum(
                "youtube", "article", "ig", "note",
                name="source_type_enum",
                create_type=False,
            ),
            nullable=True,
        ),
    )
    op.add_column("user_items", sa.Column("content_md", sa.Text(), nullable=True))
    op.add_column(
        "user_items",
        sa.Column("parsed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "user_items",
        sa.Column(
            "transcription_source",
            sa.Enum(
                "transcript", "whisper", "none",
                name="transcription_source_enum",
                create_type=False,
            ),
            nullable=True,
        ),
    )

    # ── 3. Backfill：從 content_objects 複製到 user_items ────────────────────
    # source_type: created_by_user_id IS NOT NULL → 'note'，否則沿用原值
    op.execute("""
        UPDATE user_items ui
        SET
            url                  = co.url,
            title                = co.title,
            summary              = co.summary,
            summary_i18n         = co.summary_i18n,
            thumbnail_url        = co.thumbnail_url,
            source_type          = CASE
                                     WHEN co.created_by_user_id IS NOT NULL
                                     THEN 'note'::source_type_enum
                                     ELSE co.source_type
                                   END,
            content_md           = co.content_md,
            parsed_at            = co.parsed_at,
            transcription_source = co.transcription_source
        FROM content_objects co
        WHERE ui.content_id = co.id
    """)

    # ── 4. content_objects 移除純 UserItem 欄位 ───────────────────────────────
    # title / summary / thumbnail_url 保留，CollectionItem 仍需使用
    op.drop_column("content_objects", "content_md")
    op.drop_column("content_objects", "created_by_user_id")


def downgrade() -> None:
    # 復原 content_objects 欄位
    op.add_column("content_objects", sa.Column("content_md", sa.Text(), nullable=True))
    op.add_column(
        "content_objects",
        sa.Column("created_by_user_id", postgresql.UUID(), nullable=True),
    )

    # 把 snapshot 寫回
    op.execute("""
        UPDATE content_objects co
        SET
            content_md         = ui.content_md,
            created_by_user_id = CASE
                                   WHEN ui.source_type = 'note'
                                   THEN ui.user_id
                                   ELSE NULL
                                 END
        FROM user_items ui
        WHERE ui.content_id = co.id
    """)

    # 移除 user_items snapshot 欄位
    op.drop_column("user_items", "transcription_source")
    op.drop_column("user_items", "parsed_at")
    op.drop_column("user_items", "content_md")
    op.drop_column("user_items", "source_type")
    op.drop_column("user_items", "thumbnail_url")
    op.drop_column("user_items", "summary_i18n")
    op.drop_column("user_items", "summary")
    op.drop_column("user_items", "title")
    op.drop_column("user_items", "url")
