import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

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


async def test_update_session_title_only_keeps_folder(client):
    # 只送 title 時不應動到資料夾（set_folder=False）
    mock = AsyncMock(return_value=make_session_read(title="New Title"))
    with patch("app.crud.chat.update_session", new=mock):
        resp = await client.patch(f"/chat/sessions/{TEST_SESSION_ID}", json={"title": "New Title"})
    assert resp.status_code == 200
    assert mock.call_args.kwargs["set_folder"] is False


async def test_update_session_move_to_folder(client):
    # 送 folder_id 時應移入資料夾（set_folder=True）
    moved = make_session_read(folder_id=TEST_FOLDER_ID)
    mock = AsyncMock(return_value=moved)
    with patch("app.crud.chat.update_session", new=mock):
        resp = await client.patch(
            f"/chat/sessions/{TEST_SESSION_ID}", json={"folder_id": str(TEST_FOLDER_ID)}
        )
    assert resp.status_code == 200
    assert mock.call_args.kwargs["set_folder"] is True
    assert mock.call_args.kwargs["folder_id"] == TEST_FOLDER_ID
    assert resp.json()["folder_id"] == str(TEST_FOLDER_ID)


async def test_update_session_remove_from_folder(client):
    # 明確送 folder_id=null 時應移出資料夾（set_folder=True, folder_id=None）
    mock = AsyncMock(return_value=make_session_read(folder_id=None))
    with patch("app.crud.chat.update_session", new=mock):
        resp = await client.patch(f"/chat/sessions/{TEST_SESSION_ID}", json={"folder_id": None})
    assert resp.status_code == 200
    assert mock.call_args.kwargs["set_folder"] is True
    assert mock.call_args.kwargs["folder_id"] is None


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


# ── scope（行程／報告頁 AI 懸浮球）─────────────────────────────────────────────
#
# 懸浮球沒有專屬端口，它打的就是這支 endpoint、body 多帶一個 scope。


async def _send(client, body):
    """送一則訊息，攔下背景 task 不讓它真的去跑 agent；回傳 (response, 攔到的 kwargs)。"""
    captured: dict = {}

    async def _fake_background(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs

    with patch("app.crud.chat.get_session_with_messages", new=AsyncMock(return_value=MagicMock())), \
         patch("app.crud.chat.add_message", new=AsyncMock()), \
         patch("app.crud.chat.update_session", new=AsyncMock()), \
         patch("app.crud.chat.create_assistant_placeholder",
               new=AsyncMock(return_value=MagicMock(id=TEST_SESSION_ID))), \
         patch("app.services.chat_service.run_reply_background", new=_fake_background):
        resp = await client.post(f"/chat/sessions/{TEST_SESSION_ID}/messages", json=body)
        await asyncio.sleep(0)  # 讓 create_task 排進去的假 task 跑一輪
    return resp, captured


@pytest.mark.parametrize("kind", ["trip", "report"])
async def test_send_message_forwards_scope_to_the_agent(client, kind):
    entity_id = "00000000-0000-0000-0000-0000000000ff"
    resp, captured = await _send(
        client, {"content": "把第一天改短", "scope": {"kind": kind, "id": entity_id}}
    )

    assert resp.status_code == 201
    assert captured["kwargs"]["scope"] == {"kind": kind, "id": entity_id}


async def test_send_message_without_scope_passes_none(client):
    """首頁 chat 沒有 scope。"""
    resp, captured = await _send(client, {"content": "台北有什麼好吃的"})

    assert resp.status_code == 201
    assert captured["kwargs"]["scope"] is None


@pytest.mark.parametrize("scope", [
    {"kind": "不認得的類型", "id": "00000000-0000-0000-0000-0000000000ff"},
    {"kind": "trip", "id": "not-a-uuid"},
    {"kind": "trip"},
])
async def test_send_message_rejects_malformed_scope(client, scope):
    with patch("app.crud.chat.get_session_with_messages", new=AsyncMock(return_value=MagicMock())):
        resp = await client.post(
            f"/chat/sessions/{TEST_SESSION_ID}/messages",
            json={"content": "改一下", "scope": scope},
        )
    assert resp.status_code == 422
