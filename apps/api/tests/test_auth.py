from unittest.mock import AsyncMock, patch

from tests.conftest import TEST_USER_ID, make_user_read


async def test_get_me(client):
    mock_user = make_user_read()
    with patch("app.crud.users.get_by_id", new=AsyncMock(return_value=mock_user)):
        resp = await client.get("/auth/me")
    assert resp.status_code == 200
    assert resp.json()["id"] == TEST_USER_ID


async def test_get_me_creates_user_when_not_found(client):
    mock_user = make_user_read()
    with (
        patch("app.crud.users.get_by_id", new=AsyncMock(return_value=None)),
        patch("app.crud.users.get_or_create", new=AsyncMock(return_value=mock_user)),
    ):
        resp = await client.get("/auth/me")
    assert resp.status_code == 200
    assert resp.json()["id"] == TEST_USER_ID


async def test_update_me(client):
    mock_user = make_user_read(allow_public_chain=False)
    with (
        patch("app.crud.users.get_by_id", new=AsyncMock(return_value=mock_user)),
        patch("app.crud.users.update_user", new=AsyncMock(return_value=None)),
    ):
        resp = await client.put("/auth/me", json={"allow_public_chain": False})
    assert resp.status_code == 200
    assert resp.json()["allow_public_chain"] is False


async def test_update_me_not_found(client):
    with patch("app.crud.users.get_by_id", new=AsyncMock(return_value=None)):
        resp = await client.put("/auth/me", json={"allow_public_chain": True})
    assert resp.status_code == 404


async def test_delete_me(client):
    mock_user = make_user_read()
    with (
        patch("app.crud.users.get_by_id", new=AsyncMock(return_value=mock_user)),
        patch("app.crud.users.delete_user", new=AsyncMock(return_value=None)),
    ):
        resp = await client.delete("/auth/me")
    assert resp.status_code == 204


async def test_delete_me_not_found(client):
    with patch("app.crud.users.get_by_id", new=AsyncMock(return_value=None)):
        resp = await client.delete("/auth/me")
    assert resp.status_code == 404


async def test_protected_endpoint_requires_auth(client):
    # Remove the auth override temporarily → no valid token → 401 or 403
    from app.dependencies import get_current_user
    from app.main import app

    saved = app.dependency_overrides.pop(get_current_user)
    try:
        resp = await client.get("/auth/me")
        assert resp.status_code in (401, 403)
    finally:
        app.dependency_overrides[get_current_user] = saved
