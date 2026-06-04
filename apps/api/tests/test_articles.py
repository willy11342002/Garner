from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from tests.conftest import TEST_ITEM_ID, make_item_read


async def test_list_articles(client):
    with patch("app.services.item_service.list_articles", new=AsyncMock(return_value=[make_item_read()])):
        resp = await client.get("/articles/")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


async def test_create_article(client):
    with patch("app.services.item_service.create_item", new=AsyncMock(return_value=make_item_read(is_draft=True))):
        resp = await client.post("/articles/")
    assert resp.status_code == 201


async def test_get_article(client):
    with patch("app.services.item_service.get_item", new=AsyncMock(return_value=make_item_read())):
        resp = await client.get(f"/articles/{TEST_ITEM_ID}")
    assert resp.status_code == 200
    assert resp.json()["id"] == str(TEST_ITEM_ID)


async def test_get_article_not_found(client):
    with patch(
        "app.services.item_service.get_item",
        new=AsyncMock(side_effect=HTTPException(status_code=404)),
    ):
        resp = await client.get(f"/articles/{TEST_ITEM_ID}")
    assert resp.status_code == 404


async def test_update_article(client):
    updated = make_item_read(title="New Title", is_draft=False)
    with patch("app.services.item_service.update_article", new=AsyncMock(return_value=updated)):
        resp = await client.patch(
            f"/articles/{TEST_ITEM_ID}",
            json={"title": "New Title", "is_draft": False},
        )
    assert resp.status_code == 200
    assert resp.json()["title"] == "New Title"


async def test_publish_article(client):
    with patch("app.services.item_service.publish_article", new=AsyncMock(return_value=make_item_read(is_public=True))):
        resp = await client.post(f"/articles/{TEST_ITEM_ID}/publish")
    assert resp.status_code == 200
    assert resp.json()["is_public"] is True


async def test_upload_cover_invalid_content_type(client):
    resp = await client.post(
        f"/articles/{TEST_ITEM_ID}/cover",
        files={"file": ("test.txt", b"hello", "text/plain")},
    )
    assert resp.status_code == 400


async def test_upload_cover_valid(client):
    with patch(
        "app.services.item_service.upload_article_cover",
        new=AsyncMock(return_value=make_item_read(thumbnail_url="https://r2.example.com/cover.jpg")),
    ):
        resp = await client.post(
            f"/articles/{TEST_ITEM_ID}/cover",
            files={"file": ("cover.jpg", b"fake-image-bytes", "image/jpeg")},
        )
    assert resp.status_code == 200


async def test_delete_cover(client):
    with patch(
        "app.services.item_service.delete_article_cover",
        new=AsyncMock(return_value=make_item_read(thumbnail_url=None)),
    ):
        resp = await client.delete(f"/articles/{TEST_ITEM_ID}/cover")
    assert resp.status_code == 200
