"""add missing indexes

Revision ID: 0016
Revises: 822a4cd329dc
Create Date: 2026-06-03
"""
from alembic import op

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade():
    # chat_folders: user_id
    op.create_index("ix_chat_folders_user_id", "chat_folders", ["user_id"], if_not_exists=True)

    # chat_sessions: user_id, folder_id
    op.create_index("ix_chat_sessions_user_id", "chat_sessions", ["user_id"], if_not_exists=True)
    op.create_index("ix_chat_sessions_folder_id", "chat_sessions", ["folder_id"], if_not_exists=True)

    # chat_messages: session_id
    op.create_index("ix_chat_messages_session_id", "chat_messages", ["session_id"], if_not_exists=True)

    # item_tags: tag_id (反向查詢「某 tag 有哪些 items」)
    op.create_index("ix_item_tags_tag_id", "item_tags", ["tag_id"], if_not_exists=True)

    # collection_items: content_id (反向查詢「某 content 在哪些 collections」)
    op.create_index("ix_collection_items_content_id", "collection_items", ["content_id"], if_not_exists=True)

    # collections: source_tag_id
    op.create_index("ix_collections_source_tag_id", "collections", ["source_tag_id"], if_not_exists=True)

    # user_items: composite (user_id, status) 和 (user_id, saved_at)
    op.create_index("ix_user_items_user_id_status", "user_items", ["user_id", "status"], if_not_exists=True)
    op.create_index(
        "ix_user_items_user_id_saved_at",
        "user_items",
        ["user_id", "saved_at"],
        if_not_exists=True,
    )

    # notifications: composite (user_id, is_read) 和 (user_id, created_at)
    op.create_index(
        "ix_notifications_user_id_is_read", "notifications", ["user_id", "is_read"], if_not_exists=True
    )
    op.create_index(
        "ix_notifications_user_id_created_at", "notifications", ["user_id", "created_at"], if_not_exists=True
    )


def downgrade():
    op.drop_index("ix_notifications_user_id_created_at", table_name="notifications")
    op.drop_index("ix_notifications_user_id_is_read", table_name="notifications")
    op.drop_index("ix_user_items_user_id_saved_at", table_name="user_items")
    op.drop_index("ix_user_items_user_id_status", table_name="user_items")
    op.drop_index("ix_collections_source_tag_id", table_name="collections")
    op.drop_index("ix_collection_items_content_id", table_name="collection_items")
    op.drop_index("ix_item_tags_tag_id", table_name="item_tags")
    op.drop_index("ix_chat_messages_session_id", table_name="chat_messages")
    op.drop_index("ix_chat_sessions_folder_id", table_name="chat_sessions")
    op.drop_index("ix_chat_sessions_user_id", table_name="chat_sessions")
    op.drop_index("ix_chat_folders_user_id", table_name="chat_folders")
