from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from tests.conftest import TEST_COLLECTION_ID, FAKE_NOW


def make_public_collection_orm():
    """ORM-like mock for share endpoints (no auth required)."""
    m = MagicMock()
    m.id = TEST_COLLECTION_ID
    m.title = "Public Collection"
    m.slug = "public-collection"
    m.fork_count = 5
    m.created_at = FAKE_NOW
    m.collection_items = []
    m.user = MagicMock()
    m.user.username = "author"
    m.user.avatar_url = "https://example.com/avatar.png"
    return m


async def test_get_recommendations(client):
    with patch("app.crud.collections.list_public", new=AsyncMock(return_value=[])):
        resp = await client.get("/share/recommendations")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_get_public_collection(client):
    mock_col = make_public_collection_orm()
    with patch("app.crud.collections.get_public_by_slug", new=AsyncMock(return_value=mock_col)):
        resp = await client.get("/share/public-collection")
    assert resp.status_code == 200
    data = resp.json()
    assert data["slug"] == "public-collection"
    assert data["author_username"] == "author"
    assert data["items"] == []


async def test_get_public_collection_not_found(client):
    with patch("app.crud.collections.get_public_by_slug", new=AsyncMock(return_value=None)):
        resp = await client.get("/share/does-not-exist")
    assert resp.status_code == 404
