from unittest.mock import AsyncMock, patch

from app.core.config import settings


async def test_backfill_search_index_forbidden_without_secret(client):
    resp = await client.post("/admin/backfill/search-index")
    assert resp.status_code == 403


async def test_backfill_search_index_forbidden_with_wrong_secret(client):
    resp = await client.post(
        "/admin/backfill/search-index", headers={"X-Admin-Secret": "wrong"}
    )
    assert resp.status_code == 403


async def test_backfill_search_index_ok_with_correct_secret(client, monkeypatch):
    monkeypatch.setattr(settings, "admin_secret", "test-secret")
    with patch("app.routers.admin._run_backfill_search_zh", new=AsyncMock()):
        resp = await client.post(
            "/admin/backfill/search-index", headers={"X-Admin-Secret": "test-secret"}
        )
    assert resp.status_code == 200
    assert resp.json() == {"status": "queued"}
