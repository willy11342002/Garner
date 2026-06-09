from contextlib import ExitStack
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import patch

from app.dependencies import get_current_user, get_db
from app.main import app

# ── Constants ──────────────────────────────────────────────────────────────────

TEST_USER_ID = "00000000-0000-0000-0000-000000000001"
TEST_USER_EMAIL = "test@example.com"
TEST_ITEM_ID = UUID("00000000-0000-0000-0000-000000000002")
TEST_TAG_ID = UUID("00000000-0000-0000-0000-000000000003")
TEST_COLLECTION_ID = UUID("00000000-0000-0000-0000-000000000004")
TEST_NOTIFICATION_ID = UUID("00000000-0000-0000-0000-000000000005")
TEST_FOLDER_ID = UUID("00000000-0000-0000-0000-000000000006")
TEST_SESSION_ID = UUID("00000000-0000-0000-0000-000000000007")
TEST_CONTENT_ID = UUID("00000000-0000-0000-0000-000000000010")

FAKE_NOW = datetime(2024, 1, 1, tzinfo=timezone.utc)

FAKE_JWT_PAYLOAD = {
    "sub": TEST_USER_ID,
    "email": TEST_USER_EMAIL,
    "user_metadata": {"avatar_url": "https://example.com/avatar.png"},
    "app_metadata": {"provider": "github"},
}


# ── Dependency overrides ───────────────────────────────────────────────────────

def fake_current_user():
    return FAKE_JWT_PAYLOAD


async def override_get_db():
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    result_mock.scalars.return_value = MagicMock(all=MagicMock(return_value=[]))

    mock = AsyncMock()
    mock.execute = AsyncMock(return_value=result_mock)
    mock.commit = AsyncMock(return_value=None)
    mock.refresh = AsyncMock(return_value=None)
    mock.add = MagicMock()
    mock.delete = MagicMock()
    yield mock


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture
async def client():
    app.dependency_overrides[get_current_user] = fake_current_user
    app.dependency_overrides[get_db] = override_get_db

    with ExitStack() as stack:
        stack.enter_context(patch("app.services.ai_service.load_model_configs", new=AsyncMock()))
        stack.enter_context(patch("app.core.supabase.get_supabase", new=AsyncMock(return_value=AsyncMock())))
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            yield ac

    app.dependency_overrides.clear()


# ── Schema factories ───────────────────────────────────────────────────────────

def make_user_read(**kwargs):
    from app.schemas.user import UserRead
    defaults = dict(
        id=UUID(TEST_USER_ID),
        email=TEST_USER_EMAIL,
        username="testuser",
        avatar_url="https://example.com/avatar.png",
    )
    defaults.update(kwargs)
    return UserRead(**defaults)


def make_item_read(**kwargs):
    from app.schemas.item import ItemRead
    defaults = dict(
        id=TEST_ITEM_ID,
        content_id=TEST_CONTENT_ID,
        url="https://example.com",
        title="Test Item",
        summary="Test summary",
        summary_i18n=None,
        thumbnail_url=None,
        saved_at=FAKE_NOW,
        deleted_at=None,
        parsed_at=None,
        status="active",
        source_type="article",
        transcription_source=None,
        is_owner=True,
        content_md=None,
        is_draft=False,
        is_public=False,
        tags=[],
    )
    defaults.update(kwargs)
    return ItemRead(**defaults)


def make_tag_read(**kwargs):
    from app.schemas.tag import TagRead
    defaults = dict(
        id=TEST_TAG_ID,
        name="test-tag",
        name_i18n=None,
        item_count=1,
    )
    defaults.update(kwargs)
    return TagRead(**defaults)


def make_collection_read(**kwargs):
    from app.schemas.collection import CollectionRead
    from app.models.collection import CollectionVisibility
    defaults = dict(
        id=TEST_COLLECTION_ID,
        title="Test Collection",
        visibility=CollectionVisibility.private,
        slug="test-collection",
        fork_count=0,
        created_at=FAKE_NOW,
    )
    defaults.update(kwargs)
    return CollectionRead(**defaults)


def make_collection_orm(**kwargs):
    """ORM-like mock with collection_items attribute for detail endpoints."""
    from app.models.collection import CollectionVisibility
    m = MagicMock()
    m.id = kwargs.get("id", TEST_COLLECTION_ID)
    m.title = kwargs.get("title", "Test Collection")
    m.visibility = kwargs.get("visibility", CollectionVisibility.private)
    m.slug = kwargs.get("slug", "test-collection")
    m.fork_count = kwargs.get("fork_count", 0)
    m.created_at = kwargs.get("created_at", FAKE_NOW)
    m.collection_items = kwargs.get("collection_items", [])
    return m


def make_notification_read(**kwargs):
    from app.schemas.notification import NotificationRead
    from app.models.notification import NotificationType
    defaults = dict(
        id=TEST_NOTIFICATION_ID,
        type=NotificationType.item_processed,
        title="Item processed",
        body="Your item has been processed.",
        item_id=TEST_ITEM_ID,
        is_read=False,
        created_at=FAKE_NOW,
    )
    defaults.update(kwargs)
    return NotificationRead(**defaults)


def make_folder_read(**kwargs):
    from app.schemas.chat import ChatFolderRead
    defaults = dict(
        id=TEST_FOLDER_ID,
        name="Test Folder",
        created_at=FAKE_NOW,
    )
    defaults.update(kwargs)
    return ChatFolderRead(**defaults)


def make_session_read(**kwargs):
    from app.schemas.chat import ChatSessionRead
    defaults = dict(
        id=TEST_SESSION_ID,
        folder_id=None,
        title="Test Session",
        created_at=FAKE_NOW,
        updated_at=FAKE_NOW,
    )
    defaults.update(kwargs)
    return ChatSessionRead(**defaults)
