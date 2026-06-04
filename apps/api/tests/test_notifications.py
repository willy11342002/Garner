from unittest.mock import AsyncMock, patch

from tests.conftest import TEST_NOTIFICATION_ID, make_notification_read


async def test_list_notifications(client):
    with patch(
        "app.crud.notifications.list_for_user",
        new=AsyncMock(return_value=[make_notification_read()]),
    ):
        resp = await client.get("/notifications")
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["is_read"] is False


async def test_list_notifications_unread_only(client):
    with patch(
        "app.crud.notifications.list_for_user",
        new=AsyncMock(return_value=[make_notification_read(is_read=False)]),
    ) as mock_fn:
        resp = await client.get("/notifications", params={"unread_only": True})
    assert resp.status_code == 200
    mock_fn.assert_called_once()
    _, kwargs = mock_fn.call_args
    assert kwargs.get("unread_only") is True


async def test_list_notifications_empty(client):
    with patch("app.crud.notifications.list_for_user", new=AsyncMock(return_value=[])):
        resp = await client.get("/notifications")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_mark_read(client):
    with patch("app.crud.notifications.mark_read", new=AsyncMock(return_value=None)):
        resp = await client.patch(
            "/notifications/read",
            json={"ids": [str(TEST_NOTIFICATION_ID)]},
        )
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}


async def test_mark_all_read(client):
    with patch("app.crud.notifications.mark_all_read", new=AsyncMock(return_value=None)):
        resp = await client.patch("/notifications/read-all")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
