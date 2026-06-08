"""consolidate summary/summary_i18n/content_md into single notes_md field

Revision ID: 0029
Revises: 0028
Create Date: 2026-06-08

異動說明：
- user_items 移除 summary、summary_i18n、content_md 三個欄位
- user_items 新增 notes_md（TEXT），存放純 Markdown 格式的筆記內容
- content_objects 移除 summary、summary_i18n（CollectionItem 顯示改由其他機制處理）
- 資料遷移：
    - source_type = 'note'（chat 建立文章）→ 從 content_md Tiptap JSON 轉出 Markdown
    - 其他（外部 URL）→ 直接使用 summary（AI 生成的完整 Markdown notes）
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0029"
down_revision = "0028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. 新增 notes_md ──────────────────────────────────────────────────────
    op.add_column("user_items", sa.Column("notes_md", sa.Text(), nullable=True))

    # ── 2. 建立暫時的 Tiptap JSON → Markdown 轉換函式 ─────────────────────────
    # 僅用於此次資料遷移，upgrade 結尾會 DROP
    op.execute(sa.text("""
        CREATE OR REPLACE FUNCTION _tiptap_to_md(doc jsonb) RETURNS text AS $$
        DECLARE
            result       text := '';
            node         jsonb;
            node_type    text;
            text_content text;
            bullet_lines text;
        BEGIN
            IF doc IS NULL OR doc->'content' IS NULL THEN
                RETURN '';
            END IF;

            FOR node IN SELECT * FROM jsonb_array_elements(doc->'content')
            LOOP
                node_type := node->>'type';

                IF node_type = 'heading' THEN
                    SELECT string_agg(c->>'text', '')
                    INTO text_content
                    FROM jsonb_array_elements(COALESCE(node->'content', '[]'::jsonb)) c
                    WHERE c->>'type' = 'text';
                    result := result
                        || repeat('#', COALESCE((node->'attrs'->>'level')::int, 2))
                        || ' ' || COALESCE(text_content, '')
                        || E'\n\n';

                ELSIF node_type = 'paragraph' THEN
                    SELECT string_agg(c->>'text', '')
                    INTO text_content
                    FROM jsonb_array_elements(COALESCE(node->'content', '[]'::jsonb)) c
                    WHERE c->>'type' = 'text';
                    IF text_content IS NOT NULL AND text_content <> '' THEN
                        result := result || text_content || E'\n\n';
                    END IF;

                ELSIF node_type = 'bulletList' THEN
                    SELECT string_agg(
                        '- ' || COALESCE((
                            SELECT string_agg(ct->>'text', '')
                            FROM jsonb_array_elements(COALESCE(p->'content', '[]'::jsonb)) ct
                            WHERE ct->>'type' = 'text'
                        ), ''),
                        E'\n'
                    )
                    INTO bullet_lines
                    FROM jsonb_array_elements(COALESCE(node->'content', '[]'::jsonb)) li,
                         LATERAL jsonb_array_elements(COALESCE(li->'content', '[]'::jsonb)) p
                    WHERE p->>'type' = 'paragraph';
                    IF bullet_lines IS NOT NULL AND bullet_lines <> '' THEN
                        result := result || bullet_lines || E'\n\n';
                    END IF;
                END IF;
            END LOOP;

            RETURN trim(result);
        END;
        $$ LANGUAGE plpgsql;
    """))

    # ── 3. 資料遷移 ───────────────────────────────────────────────────────────
    op.execute(sa.text("""
        UPDATE user_items
        SET notes_md = CASE
            WHEN source_type = 'note' AND content_md IS NOT NULL
                THEN _tiptap_to_md(content_md::jsonb)
            ELSE summary
        END
    """))

    # ── 4. 清除暫時函式 ───────────────────────────────────────────────────────
    op.execute(sa.text("DROP FUNCTION IF EXISTS _tiptap_to_md(jsonb)"))

    # ── 5. 移除 user_items 舊欄位 ─────────────────────────────────────────────
    op.drop_column("user_items", "content_md")
    op.drop_column("user_items", "summary_i18n")
    op.drop_column("user_items", "summary")

    # ── 6. 移除 content_objects 顯示欄位 ─────────────────────────────────────
    op.drop_column("content_objects", "summary_i18n")
    op.drop_column("content_objects", "summary")


def downgrade() -> None:
    # ── 復原 content_objects ──────────────────────────────────────────────────
    op.add_column("content_objects", sa.Column("summary", sa.Text(), nullable=True))
    op.add_column(
        "content_objects",
        sa.Column("summary_i18n", postgresql.JSONB(), nullable=True),
    )

    # ── 復原 user_items ───────────────────────────────────────────────────────
    op.add_column("user_items", sa.Column("summary", sa.Text(), nullable=True))
    op.add_column(
        "user_items",
        sa.Column("summary_i18n", postgresql.JSONB(), nullable=True),
    )
    op.add_column("user_items", sa.Column("content_md", sa.Text(), nullable=True))

    # best-effort backfill：notes_md → summary（格式相同；summary_i18n/content_md 無法還原）
    op.execute(sa.text("UPDATE user_items SET summary = notes_md"))

    # ── 移除 notes_md ─────────────────────────────────────────────────────────
    op.drop_column("user_items", "notes_md")
