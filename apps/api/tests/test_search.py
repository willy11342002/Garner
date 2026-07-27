from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest

from app.services import search_service
from tests.conftest import make_item_read


def _make_user_item(item_id, title="Title", notes_md="Notes"):
    ui = MagicMock()
    ui.id = item_id
    ui.url = "https://example.com"
    ui.title = title
    ui.notes_md = notes_md
    ui.thumbnail_url = None
    ui.saved_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    ui.deleted_at = None
    ui.parsed_at = None
    ui.source_type = "article"
    ui.status = "active"
    return ui


def test_rrf_fuse_combines_ranks_from_overlapping_lists():
    id_a, id_b, id_c = UUID(int=1), UUID(int=2), UUID(int=3)
    scores = search_service._rrf_fuse([id_a, id_b], [id_b, id_c])
    assert scores[id_a] == pytest.approx(1 / 61)
    assert scores[id_c] == pytest.approx(1 / 62)
    # id_b 同時出現在兩個排名清單裡（rank 2 + rank 1），分數應為兩者加總、高於只出現一次的
    assert scores[id_b] == pytest.approx(1 / 62 + 1 / 61)
    assert scores[id_b] > scores[id_a]
    assert scores[id_b] > scores[id_c]


async def test_semantic_search_fuses_candidates_and_orders_by_rerank():
    id_vector_only, id_bm25_only = UUID(int=1), UUID(int=2)
    item_vector = _make_user_item(id_vector_only, title="Vector Hit")
    item_bm25 = _make_user_item(id_bm25_only, title="BM25 Hit")

    with (
        patch("app.services.search_service.ai_service.embed", new=AsyncMock(return_value=[0.1])),
        patch("app.services.search_service.ai_service.segment", new=AsyncMock(return_value="query")),
        patch("app.services.search_service._get_cutoff", new=AsyncMock(return_value=0.45)),
        patch(
            "app.services.search_service._merge_semantic",
            new=AsyncMock(return_value={id_vector_only: (item_vector, 0.1)}),
        ),
        patch(
            "app.services.search_service.crud_items.bm25_search",
            new=AsyncMock(return_value=[(item_bm25, 0.9)]),
        ),
        patch(
            "app.services.search_service.ai_service.rerank",
            new=AsyncMock(return_value=[
                {"id": str(id_bm25_only), "text": "...", "score": 0.9},
                {"id": str(id_vector_only), "text": "...", "score": 0.2},
            ]),
        ),
    ):
        result = await search_service.semantic_search(AsyncMock(), UUID(int=99), "query", page=1)

    # 兩個候選（分別只被向量/BM25 命中）都要進最終結果，順序照 rerank 分數排
    assert [it.id for it in result.items] == [id_bm25_only, id_vector_only]
    assert result.has_next is False


async def test_search_returns_results(client):
    with patch("app.services.search_service.text_search", new=AsyncMock(return_value=[make_item_read()])):
        resp = await client.get("/search/", params={"q": "python"})
    assert resp.status_code == 200
    assert len(resp.json()) == 1


async def test_search_empty_results(client):
    with patch("app.services.search_service.text_search", new=AsyncMock(return_value=[])):
        resp = await client.get("/search/", params={"q": "nonexistent"})
    assert resp.status_code == 200
    assert resp.json() == []


async def test_search_missing_query(client):
    resp = await client.get("/search/")
    assert resp.status_code == 422
