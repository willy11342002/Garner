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
    # backfill 的實作已移到 app/workers/backfill.py，router 只負責驗證 secret 與排程。
    # patch 的是 router 匯入進來的名稱，不是原始模組。
    with patch("app.routers.admin.backfill_search_zh", new=AsyncMock()):
        resp = await client.post(
            "/admin/backfill/search-index", headers={"X-Admin-Secret": "test-secret"}
        )
    assert resp.status_code == 200
    assert resp.json() == {"status": "queued"}
