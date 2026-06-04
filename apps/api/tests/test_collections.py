from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from tests.conftest import (
    TEST_COLLECTION_ID,
    TEST_CONTENT_ID,
    TEST_ITEM_ID,
    make_collection_orm,
    make_collection_read,
    make_item_read,
)


async def test_list_collections(client):
    with patch("app.crud.collections.get_all", new=AsyncMock(return_value=[make_collection_read()])):
        resp = await client.get("/collections/")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


async def test_list_collections_empty(client):
    with patch("app.crud.collections.get_all", new=AsyncMock(return_value=[])):
        resp = await client.get("/collections/")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_create_collection(client):
    with patch("app.crud.collections.create", new=AsyncMock(return_value=make_collection_read())):
        resp = await client.post(
            "/collections/",
            json={"title": "My Collection", "slug": "my-collection", "visibility": "private"},
        )
    assert resp.status_code == 201
    assert resp.json()["title"] == "Test Collection"


async def test_get_collection(client):
    mock_col = make_collection_orm()
    with patch("app.crud.collections.get_one", new=AsyncMock(return_value=mock_col)):
        resp = await client.get(f"/collections/{TEST_COLLECTION_ID}")
    assert resp.status_code == 200
    assert resp.json()["id"] == str(TEST_COLLECTION_ID)
    assert resp.json()["items"] == []


async def test_get_collection_not_found(client):
    with patch("app.crud.collections.get_one", new=AsyncMock(return_value=None)):
        resp = await client.get(f"/collections/{TEST_COLLECTION_ID}")
    assert resp.status_code == 404


async def test_update_collection(client):
    updated = make_collection_read(title="Updated")
    with (
        patch("app.crud.collections.get_one", new=AsyncMock(return_value=make_collection_orm())),
        patch("app.crud.collections.update", new=AsyncMock(return_value=updated)),
    ):
        resp = await client.patch(f"/collections/{TEST_COLLECTION_ID}", json={"title": "Updated"})
    assert resp.status_code == 200
    assert resp.json()["title"] == "Updated"


async def test_update_collection_not_found(client):
    with patch("app.crud.collections.get_one", new=AsyncMock(return_value=None)):
        resp = await client.patch(f"/collections/{TEST_COLLECTION_ID}", json={"title": "X"})
    assert resp.status_code == 404


async def test_delete_collection(client):
    with (
        patch("app.crud.collections.get_one", new=AsyncMock(return_value=make_collection_orm())),
        patch("app.crud.collections.delete_collection", new=AsyncMock(return_value=None)),
    ):
        resp = await client.delete(f"/collections/{TEST_COLLECTION_ID}")
    assert resp.status_code == 204


async def test_delete_collection_not_found(client):
    with patch("app.crud.collections.get_one", new=AsyncMock(return_value=None)):
        resp = await client.delete(f"/collections/{TEST_COLLECTION_ID}")
    assert resp.status_code == 404


async def test_add_item_to_collection(client):
    mock_item = MagicMock()
    with (
        patch("app.crud.collections.get_one", new=AsyncMock(return_value=make_collection_orm())),
        patch("app.crud.items.get_by_content_id", new=AsyncMock(return_value=mock_item)),
        patch("app.crud.collections.add_item", new=AsyncMock(return_value=None)),
    ):
        resp = await client.post(
            f"/collections/{TEST_COLLECTION_ID}/items",
            params={"content_id": str(TEST_CONTENT_ID)},
        )
    assert resp.status_code == 204


async def test_add_item_to_collection_not_found(client):
    with patch("app.crud.collections.get_one", new=AsyncMock(return_value=None)):
        resp = await client.post(
            f"/collections/{TEST_COLLECTION_ID}/items",
            params={"content_id": str(TEST_CONTENT_ID)},
        )
    assert resp.status_code == 404


async def test_remove_item_from_collection(client):
    with (
        patch("app.crud.collections.get_one", new=AsyncMock(return_value=make_collection_orm())),
        patch("app.crud.collections.remove_item", new=AsyncMock(return_value=None)),
    ):
        resp = await client.delete(
            f"/collections/{TEST_COLLECTION_ID}/items/{TEST_CONTENT_ID}"
        )
    assert resp.status_code == 204


async def test_fork_collection(client):
    source = make_collection_orm()
    forked = make_collection_read()
    with (
        patch("app.crud.collections.get_by_id_with_items", new=AsyncMock(return_value=source)),
        patch("app.crud.collections.fork_collection", new=AsyncMock(return_value=forked)),
    ):
        resp = await client.post(
            f"/collections/{TEST_COLLECTION_ID}/fork",
            json={"visibility": "link", "content_ids": []},
        )
    assert resp.status_code == 201


async def test_fork_collection_not_found(client):
    with patch("app.crud.collections.get_by_id_with_items", new=AsyncMock(return_value=None)):
        resp = await client.post(
            f"/collections/{TEST_COLLECTION_ID}/fork",
            json={"visibility": "link", "content_ids": []},
        )
    assert resp.status_code == 404
