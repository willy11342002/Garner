from unittest.mock import AsyncMock, patch

from tests.conftest import make_item_read


async def test_search_returns_results(client):
    with patch("app.services.search_service.search", new=AsyncMock(return_value=[make_item_read()])):
        resp = await client.get("/search/", params={"q": "python"})
    assert resp.status_code == 200
    assert len(resp.json()) == 1


async def test_search_empty_results(client):
    with patch("app.services.search_service.search", new=AsyncMock(return_value=[])):
        resp = await client.get("/search/", params={"q": "nonexistent"})
    assert resp.status_code == 200
    assert resp.json() == []


async def test_search_missing_query(client):
    resp = await client.get("/search/")
    assert resp.status_code == 422
