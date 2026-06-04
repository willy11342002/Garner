from unittest.mock import AsyncMock, MagicMock, patch

from tests.conftest import TEST_FOLDER_ID, TEST_SESSION_ID, make_folder_read, make_session_read


# ── Folders ────────────────────────────────────────────────────────────────────

async def test_list_folders(client):
    with patch("app.crud.chat.list_folders", new=AsyncMock(return_value=[make_folder_read()])):
        resp = await client.get("/chat/folders")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


async def test_create_folder(client):
    with patch("app.crud.chat.create_folder", new=AsyncMock(return_value=make_folder_read())):
        resp = await client.post("/chat/folders", json={"name": "Test Folder"})
    assert resp.status_code == 201
    assert resp.json()["name"] == "Test Folder"


async def test_update_folder(client):
    updated = make_folder_read(name="Renamed Folder")
    with patch("app.crud.chat.update_folder", new=AsyncMock(return_value=updated)):
        resp = await client.patch(f"/chat/folders/{TEST_FOLDER_ID}", json={"name": "Renamed Folder"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "Renamed Folder"


async def test_update_folder_not_found(client):
    with patch("app.crud.chat.update_folder", new=AsyncMock(return_value=None)):
        resp = await client.patch(f"/chat/folders/{TEST_FOLDER_ID}", json={"name": "X"})
    assert resp.status_code == 404


async def test_delete_folder(client):
    with patch("app.crud.chat.delete_folder", new=AsyncMock(return_value=True)):
        resp = await client.delete(f"/chat/folders/{TEST_FOLDER_ID}")
    assert resp.status_code == 204


async def test_delete_folder_not_found(client):
    with patch("app.crud.chat.delete_folder", new=AsyncMock(return_value=False)):
        resp = await client.delete(f"/chat/folders/{TEST_FOLDER_ID}")
    assert resp.status_code == 404


# ── Sessions ───────────────────────────────────────────────────────────────────

async def test_list_sessions(client):
    with patch("app.crud.chat.list_sessions", new=AsyncMock(return_value=[make_session_read()])):
        resp = await client.get("/chat/sessions")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


async def test_create_session(client):
    with patch("app.crud.chat.create_session", new=AsyncMock(return_value=make_session_read())):
        resp = await client.post("/chat/sessions", json={})
    assert resp.status_code == 201


async def test_get_session(client):
    from app.schemas.chat import ChatSessionDetail
    mock_session = ChatSessionDetail(
        id=TEST_SESSION_ID,
        folder_id=None,
        title="Test Session",
        created_at=make_session_read().created_at,
        updated_at=make_session_read().updated_at,
        messages=[],
    )
    with patch("app.crud.chat.get_session_with_messages", new=AsyncMock(return_value=mock_session)):
        resp = await client.get(f"/chat/sessions/{TEST_SESSION_ID}")
    assert resp.status_code == 200
    assert resp.json()["id"] == str(TEST_SESSION_ID)
    assert resp.json()["messages"] == []


async def test_get_session_not_found(client):
    with patch("app.crud.chat.get_session_with_messages", new=AsyncMock(return_value=None)):
        resp = await client.get(f"/chat/sessions/{TEST_SESSION_ID}")
    assert resp.status_code == 404


async def test_update_session(client):
    updated = make_session_read(title="New Title")
    with patch("app.crud.chat.update_session", new=AsyncMock(return_value=updated)):
        resp = await client.patch(f"/chat/sessions/{TEST_SESSION_ID}", json={"title": "New Title"})
    assert resp.status_code == 200
    assert resp.json()["title"] == "New Title"


async def test_update_session_not_found(client):
    with patch("app.crud.chat.update_session", new=AsyncMock(return_value=None)):
        resp = await client.patch(f"/chat/sessions/{TEST_SESSION_ID}", json={"title": "X"})
    assert resp.status_code == 404


async def test_delete_session(client):
    with patch("app.crud.chat.delete_session", new=AsyncMock(return_value=True)):
        resp = await client.delete(f"/chat/sessions/{TEST_SESSION_ID}")
    assert resp.status_code == 204


async def test_delete_session_not_found(client):
    with patch("app.crud.chat.delete_session", new=AsyncMock(return_value=False)):
        resp = await client.delete(f"/chat/sessions/{TEST_SESSION_ID}")
    assert resp.status_code == 404


# ── Messages ───────────────────────────────────────────────────────────────────

async def test_send_message_empty_content(client):
    mock_session = MagicMock()
    with patch("app.crud.chat.get_session_with_messages", new=AsyncMock(return_value=mock_session)):
        resp = await client.post(
            f"/chat/sessions/{TEST_SESSION_ID}/messages",
            json={"content": "   "},
        )
    assert resp.status_code == 422


async def test_send_message_session_not_found(client):
    with patch("app.crud.chat.get_session_with_messages", new=AsyncMock(return_value=None)):
        resp = await client.post(
            f"/chat/sessions/{TEST_SESSION_ID}/messages",
            json={"content": "Hello"},
        )
    assert resp.status_code == 404
