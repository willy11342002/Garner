from unittest.mock import AsyncMock, patch
from uuid import uuid4

from fastapi import HTTPException

from tests.conftest import TEST_ITEM_ID, TEST_TAG_ID, make_item_read, make_tag_read


# ── List / detail ──────────────────────────────────────────────────────────────

async def test_list_items(client):
    from app.schemas.item import ItemPage
    page = ItemPage(items=[make_item_read()], total=1, page=1, page_size=25)
    with patch("app.services.item_service.list_items_page", new=AsyncMock(return_value=page)):
        resp = await client.get("/items/")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["items"]) == 1
    assert body["total"] == 1


async def test_list_items_empty(client):
    from app.schemas.item import ItemPage
    page = ItemPage(items=[], total=0, page=1, page_size=25)
    with patch("app.services.item_service.list_items_page", new=AsyncMock(return_value=page)):
        resp = await client.get("/items/")
    assert resp.status_code == 200
    assert resp.json()["items"] == []


async def test_get_item(client):
    with patch("app.services.item_service.get_item", new=AsyncMock(return_value=make_item_read())):
        resp = await client.get(f"/items/{TEST_ITEM_ID}")
    assert resp.status_code == 200
    assert resp.json()["id"] == str(TEST_ITEM_ID)


async def test_get_item_not_found(client):
    with patch(
        "app.services.item_service.get_item",
        new=AsyncMock(side_effect=HTTPException(status_code=404)),
    ):
        resp = await client.get(f"/items/{TEST_ITEM_ID}")
    assert resp.status_code == 404


async def test_list_archived(client):
    with patch("app.services.item_service.list_archived_items", new=AsyncMock(return_value=[])):
        resp = await client.get("/items/archived")
    assert resp.status_code == 200


# ── Create ─────────────────────────────────────────────────────────────────────

async def test_create_item(client):
    from app.services.item_service import _ItemCreateResult
    result = _ItemCreateResult(item=make_item_read(), needs_processing=False)
    with patch("app.services.item_service.prepare_item_create", new=AsyncMock(return_value=result)):
        resp = await client.post(
            "/items/",
            json={"url": "https://example.com"},
            headers={"X-Response-Mode": "async"},
        )
    assert resp.status_code == 201
    assert resp.json()["url"] == "https://example.com"


async def test_create_item_invalid_url(client):
    resp = await client.post("/items/", json={"url": "not-a-url"})
    assert resp.status_code == 422


async def test_create_in_app_note(client):
    from app.services.item_service import _ItemCreateResult
    result = _ItemCreateResult(item=make_item_read(url="garner://note"), needs_processing=False)
    with patch("app.services.item_service.prepare_item_create", new=AsyncMock(return_value=result)):
        resp = await client.post("/items/", json={"title": "My note", "raw_content": "some text"})
    assert resp.status_code == 201


# ── Update / delete ────────────────────────────────────────────────────────────

async def test_update_item(client):
    updated = make_item_read(title="Updated Title")
    with patch("app.services.item_service.update_item", new=AsyncMock(return_value=updated)):
        resp = await client.patch(f"/items/{TEST_ITEM_ID}", json={"title": "Updated Title"})
    assert resp.status_code == 200
    assert resp.json()["title"] == "Updated Title"


async def test_delete_item(client):
    with patch("app.services.item_service.delete_item", new=AsyncMock(return_value=None)):
        resp = await client.delete(f"/items/{TEST_ITEM_ID}")
    assert resp.status_code == 204


# ── Tag sub-routes ─────────────────────────────────────────────────────────────

async def test_list_item_tags(client):
    # db mock returns empty scalars by default
    resp = await client.get(f"/items/{TEST_ITEM_ID}/tags")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_attach_tag(client):
    mock_tag = make_tag_read()
    with (
        patch("app.crud.tags.get_or_create", new=AsyncMock(return_value=mock_tag)),
        patch("app.crud.tags.attach_tag", new=AsyncMock(return_value=None)),
    ):
        resp = await client.post(f"/items/{TEST_ITEM_ID}/tags", json={"name": "test-tag"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "test-tag"


async def test_detach_tag(client):
    with patch("app.crud.tags.detach_tag", new=AsyncMock(return_value=None)):
        resp = await client.delete(f"/items/{TEST_ITEM_ID}/tags/{TEST_TAG_ID}")
    assert resp.status_code == 204
