from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.main import app
from app.routers.admin import _require_admin
from tests.conftest import override_get_db

ADMIN_HEADER = {"X-Admin-Secret": "test-secret"}


@pytest.fixture
async def admin_client():
    """Client with admin dependency overridden (no real secret check)."""
    from contextlib import ExitStack
    from app.dependencies import get_db

    app.dependency_overrides[_require_admin] = lambda: None
    app.dependency_overrides[get_db] = override_get_db

    with ExitStack() as stack:
        stack.enter_context(patch("app.services.ai_service.load_model_configs", new=AsyncMock()))
        stack.enter_context(patch("app.core.supabase.get_supabase", new=AsyncMock(return_value=AsyncMock())))
        from httpx import AsyncClient, ASGITransport
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            yield ac

    app.dependency_overrides.clear()


async def test_upload_youtube_cookies(admin_client):
    resp = await admin_client.post(
        "/admin/youtube-cookies",
        files={"file": ("cookies.txt", b"# Netscape HTTP Cookie File\nexample.com\n", "text/plain")},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


async def test_get_cookies_status_not_set(admin_client):
    # db mock returns None for scalar_one_or_none by default
    resp = await admin_client.get("/admin/youtube-cookies/status")
    assert resp.status_code == 200
    assert resp.json()["set"] is False


async def test_get_cookies_status_set(admin_client):
    from unittest.mock import MagicMock, AsyncMock
    from app.dependencies import get_db

    setting_mock = MagicMock()
    setting_mock.value = "# cookies content"
    setting_mock.updated_at = None

    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = setting_mock

    async def db_with_setting():
        mock = AsyncMock()
        mock.execute = AsyncMock(return_value=result_mock)
        mock.commit = AsyncMock()
        yield mock

    app.dependency_overrides[get_db] = db_with_setting
    resp = await admin_client.get("/admin/youtube-cookies/status")
    assert resp.status_code == 200
    assert resp.json()["set"] is True
    app.dependency_overrides[get_db] = override_get_db


async def test_delete_youtube_cookies(admin_client):
    resp = await admin_client.delete("/admin/youtube-cookies")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


async def test_admin_endpoint_forbidden_without_secret(client):
    # Provide the header but with a wrong value.
    # Default settings.admin_secret is "" → condition `not settings.admin_secret`
    # is True, so any request raises 403 regardless of the header value.
    resp = await client.post(
        "/admin/youtube-cookies",
        headers={"X-Admin-Secret": "wrong-secret"},
        files={"file": ("cookies.txt", b"data", "text/plain")},
    )
    assert resp.status_code == 403
