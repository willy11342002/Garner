from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from uuid import UUID

from tests.conftest import TEST_ITEM_ID, FAKE_NOW


# ── Stats ──────────────────────────────────────────────────────────────────────

async def test_get_stats(client):
    from app.schemas.explore import ExploreStats
    mock_stats = ExploreStats(total_items=10, public_collections=2, weekly_new=3)
    with patch("app.services.explore_service.get_stats", new=AsyncMock(return_value=mock_stats)):
        resp = await client.get("/explore/stats")
    assert resp.status_code == 200
    assert resp.json()["total_items"] == 10


# ── Browse ─────────────────────────────────────────────────────────────────────

async def test_browse_public_collections(client):
    with patch(
        "app.services.explore_service.browse_public_collections",
        new=AsyncMock(return_value=[]),
    ):
        resp = await client.get("/explore/browse")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_browse_with_filters(client):
    with patch(
        "app.services.explore_service.browse_public_collections",
        new=AsyncMock(return_value=[]),
    ):
        resp = await client.get("/explore/browse", params={"q": "python", "tag": "AI"})
    assert resp.status_code == 200


# ── Focus ──────────────────────────────────────────────────────────────────────

async def test_focus_query(client):
    from app.schemas.explore import FocusResult
    mock_result = FocusResult(synthesis="AI insights here.", sources=[])
    with patch("app.services.explore_service.focus_query", new=AsyncMock(return_value=mock_result)):
        resp = await client.post("/explore/focus", json={"query": "What did I learn about AI?"})
    assert resp.status_code == 200
    assert "synthesis" in resp.json()


async def test_focus_query_empty_string(client):
    resp = await client.post("/explore/focus", json={"query": "   "})
    assert resp.status_code == 422


async def test_focus_query_service_error(client):
    with patch(
        "app.services.explore_service.focus_query",
        new=AsyncMock(side_effect=RuntimeError("OpenRouter down")),
    ):
        resp = await client.post("/explore/focus", json={"query": "test"})
    assert resp.status_code == 503


# ── Surprise ───────────────────────────────────────────────────────────────────

async def test_get_surprise(client):
    from app.schemas.explore import SurpriseResult
    mock_result = SurpriseResult(insights=[])
    with patch("app.services.explore_service.get_surprise", new=AsyncMock(return_value=mock_result)):
        resp = await client.get("/explore/surprise")
    assert resp.status_code == 200
    assert "insights" in resp.json()


# ── Chain ──────────────────────────────────────────────────────────────────────

async def test_chain_start(client):
    with patch(
        "app.services.explore_service.get_chain_start_items",
        new=AsyncMock(return_value=[]),
    ):
        resp = await client.get("/explore/chain/start")
    assert resp.status_code == 200


async def test_chain_start_invalid_type(client):
    resp = await client.get("/explore/chain/start", params={"type": "invalid"})
    assert resp.status_code == 422


async def test_chain_next(client):
    with patch(
        "app.services.explore_service.get_chain_candidates",
        new=AsyncMock(return_value=[]),
    ):
        resp = await client.get("/explore/chain/next", params={"item_id": str(TEST_ITEM_ID)})
    assert resp.status_code == 200


async def test_chain_hop(client):
    from app.schemas.explore import ChainHopAnalysis
    mock_result = ChainHopAnalysis(
        connection="They both relate to Python.",
        ideation="Build a project combining both.",
        question="What is the deeper connection?",
    )
    item_a = UUID("00000000-0000-0000-0000-000000000011")
    item_b = UUID("00000000-0000-0000-0000-000000000012")
    with patch("app.services.explore_service.analyze_hop", new=AsyncMock(return_value=mock_result)):
        resp = await client.post(
            "/explore/chain/hop",
            json={"from_item_id": str(item_a), "to_item_id": str(item_b)},
        )
    assert resp.status_code == 200
    assert "connection" in resp.json()


async def test_chain_full(client):
    from app.schemas.explore import ChainFullAnalysis
    mock_result = ChainFullAnalysis(analysis="Interesting pattern detected.")
    item_a = UUID("00000000-0000-0000-0000-000000000011")
    item_b = UUID("00000000-0000-0000-0000-000000000012")
    with patch("app.services.explore_service.analyze_full_chain", new=AsyncMock(return_value=mock_result)):
        resp = await client.post(
            "/explore/chain/full",
            json={"item_ids": [str(item_a), str(item_b)]},
        )
    assert resp.status_code == 200
    assert resp.json()["analysis"] == "Interesting pattern detected."


async def test_chain_full_too_few_items(client):
    item_a = UUID("00000000-0000-0000-0000-000000000011")
    resp = await client.post(
        "/explore/chain/full",
        json={"item_ids": [str(item_a)]},
    )
    assert resp.status_code == 422
