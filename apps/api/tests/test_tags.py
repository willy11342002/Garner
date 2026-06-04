from unittest.mock import AsyncMock, patch

from tests.conftest import TEST_TAG_ID, make_item_read, make_tag_read


async def test_list_tags(client):
    with patch("app.crud.tags.get_all", new=AsyncMock(return_value=[make_tag_read()])):
        resp = await client.get("/tags/")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


async def test_list_tags_empty(client):
    with patch("app.crud.tags.get_all", new=AsyncMock(return_value=[])):
        resp = await client.get("/tags/")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_create_tag(client):
    mock_tag = make_tag_read(name="new-tag")
    with patch("app.crud.tags.get_or_create", new=AsyncMock(return_value=mock_tag)):
        resp = await client.post("/tags/", json={"name": "new-tag"})
    assert resp.status_code == 201
    assert resp.json()["name"] == "new-tag"


async def test_get_tag(client):
    with patch("app.crud.tags.get_one", new=AsyncMock(return_value=make_tag_read())):
        resp = await client.get(f"/tags/{TEST_TAG_ID}")
    assert resp.status_code == 200
    assert resp.json()["id"] == str(TEST_TAG_ID)


async def test_get_tag_not_found(client):
    with patch("app.crud.tags.get_one", new=AsyncMock(return_value=None)):
        resp = await client.get(f"/tags/{TEST_TAG_ID}")
    assert resp.status_code == 404


async def test_update_tag(client):
    updated = make_tag_read(name="renamed-tag")
    with (
        patch("app.crud.tags.get_one", new=AsyncMock(return_value=make_tag_read())),
        patch("app.crud.tags.update", new=AsyncMock(return_value=updated)),
    ):
        resp = await client.patch(f"/tags/{TEST_TAG_ID}", json={"name": "renamed-tag"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "renamed-tag"


async def test_update_tag_not_found(client):
    with patch("app.crud.tags.get_one", new=AsyncMock(return_value=None)):
        resp = await client.patch(f"/tags/{TEST_TAG_ID}", json={"name": "renamed-tag"})
    assert resp.status_code == 404


async def test_delete_tag(client):
    with (
        patch("app.crud.tags.get_one", new=AsyncMock(return_value=make_tag_read())),
        patch("app.crud.tags.delete_tag", new=AsyncMock(return_value=None)),
    ):
        resp = await client.delete(f"/tags/{TEST_TAG_ID}")
    assert resp.status_code == 204


async def test_delete_tag_not_found(client):
    with patch("app.crud.tags.get_one", new=AsyncMock(return_value=None)):
        resp = await client.delete(f"/tags/{TEST_TAG_ID}")
    assert resp.status_code == 404


async def test_list_tag_items(client):
    item = make_item_read()
    with (
        patch("app.crud.tags.get_one", new=AsyncMock(return_value=make_tag_read())),
        patch("app.crud.tags.get_items_by_tag", new=AsyncMock(return_value=[])),
    ):
        resp = await client.get(f"/tags/{TEST_TAG_ID}/items")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_list_tag_items_not_found(client):
    with patch("app.crud.tags.get_one", new=AsyncMock(return_value=None)):
        resp = await client.get(f"/tags/{TEST_TAG_ID}/items")
    assert resp.status_code == 404
