"""縮圖快取的迴歸測試。

背景：quick_meta 會在建立當下把平台的短期簽名網址寫進 thumbnail_url，
背景 pipeline 當年只在欄位空白時才覆寫，導致 Storage 有快取、DB 卻留著幾天就
過期的網址。以下測試釘住「快取好的網址一定會蓋掉平台網址」這條規則。
"""
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

PLATFORM_URL = "https://scontent.cdninstagram.com/v/t51.jpg?oe=68B0C0DE"
CACHED_URL = (
    "https://proj.supabase.co/storage/v1/object/public/thumbnails/thumbnails/abc.jpg"
)


# ── provider 端：抓得到就快取，抓不到才退回平台網址 ─────────────────────────────

class _Provider:
    """只借 ContentProvider 的 _resolve_thumbnail，不實作抽象方法。"""

    def __init__(self):
        from app.providers.base import ContentProvider
        self._resolve = ContentProvider._resolve_thumbnail.__get__(self, ContentProvider)


async def test_resolve_thumbnail_marks_cached_url():
    provider = _Provider()
    with (
        patch("app.services.apify_service.download_bytes", new=AsyncMock(return_value=b"jpg")),
        patch("app.services.thumbnail_service.cache", new=AsyncMock(return_value=CACHED_URL)),
    ):
        url, cached = await provider._resolve("abc", PLATFORM_URL)
    assert (url, cached) == (CACHED_URL, True)


async def test_resolve_thumbnail_falls_back_to_platform_url_when_upload_fails():
    provider = _Provider()
    with (
        patch("app.services.apify_service.download_bytes", new=AsyncMock(return_value=b"jpg")),
        patch("app.services.thumbnail_service.cache", new=AsyncMock(side_effect=RuntimeError)),
    ):
        url, cached = await provider._resolve("abc", PLATFORM_URL)
    # 退路網址會過期，所以 cached 必須是 False，下游才知道不能長期保存
    assert (url, cached) == (PLATFORM_URL, False)


async def test_resolve_thumbnail_without_source():
    provider = _Provider()
    assert await provider._resolve("abc", None) == (None, False)


# ── worker 端：快取網址覆寫 quick_meta 留下的平台網址 ───────────────────────────

@asynccontextmanager
async def _fake_session(db):
    yield db


def _patch_fetch_core(user_item, info):
    db = MagicMock()
    db.get = AsyncMock(return_value=user_item)
    db.commit = AsyncMock()
    provider = MagicMock()
    provider.fetch_info = AsyncMock(return_value=info)
    provider.fetch_content = AsyncMock(return_value="raw")
    return (
        patch("app.workers.ingest_graph.AsyncSessionLocal", lambda: _fake_session(db)),
        patch("app.providers.get_provider", return_value=provider),
    )


def _user_item(thumbnail_url):
    return SimpleNamespace(
        id=UUID("00000000-0000-0000-0000-0000000000aa"),
        title="t",
        thumbnail_url=thumbnail_url,
        duration_sec=None,
        raw_data=None,
        notes_md=None,
        source_type="ig",
    )


def _state(item):
    return {
        "user_item_id": str(item.id),
        "url": "https://www.instagram.com/p/abc/",
        "user_id": str(uuid4()),
        "max_video_sec": 600,
        "raw_content": None,
    }


@pytest.mark.parametrize(
    ("existing", "cached", "incoming", "expected"),
    [
        # quick_meta 的平台網址會過期 → 快取好的網址必須蓋掉它
        (PLATFORM_URL, True, CACHED_URL, CACHED_URL),
        # 快取失敗時拿到的還是平台網址 → 不要拿一條過期網址換掉另一條
        (PLATFORM_URL, False, "https://other.cdn/x.jpg", PLATFORM_URL),
        # 欄位本來就空的（quick_meta 逾時）→ 還是要補上，即使沒快取成功
        (None, False, PLATFORM_URL, PLATFORM_URL),
    ],
)
async def test_fetch_core_thumbnail_overwrite(existing, cached, incoming, expected):
    from app.providers.base import FetchInfo
    from app.workers.ingest_graph import _fetch_core

    item = _user_item(existing)
    info = FetchInfo(
        raw_data={"a": 1},
        title="new",
        thumbnail_url=incoming,
        thumbnail_cached=cached,
        raw_content="raw",
    )
    session_patch, provider_patch = _patch_fetch_core(item, info)
    with session_patch, provider_patch:
        await _fetch_core(_state(item))

    assert item.thumbnail_url == expected


# ── backfill：把站外網址換回 Storage ───────────────────────────────────────────

async def test_backfill_thumbnails_relinks_and_recaches():
    from app.workers import backfill

    relinkable = _user_item(PLATFORM_URL)
    recacheable = _user_item("https://p16-sign.tiktokcdn.com/x.jpg?x-expires=1")
    unrecoverable = _user_item("https://dead.cdn/gone.jpg")
    recacheable.id = UUID("00000000-0000-0000-0000-0000000000bb")
    unrecoverable.id = UUID("00000000-0000-0000-0000-0000000000cc")
    rows = [relinkable, recacheable, unrecoverable]

    db = MagicMock()
    db.commit = AsyncMock()
    # 第二輪回空陣列，讓游標迴圈收斂
    get_rows = AsyncMock(side_effect=[rows, []])

    async def fake_find_cached(item_id):
        return CACHED_URL if item_id == str(relinkable.id) else None

    async def fake_download(url):
        return b"jpg" if url == recacheable.thumbnail_url else None

    with (
        patch("app.workers.backfill.AsyncSessionLocal", lambda: _fake_session(db)),
        patch("app.crud.items.get_external_thumbnails", new=get_rows),
        patch("app.services.thumbnail_service.find_cached", new=AsyncMock(side_effect=fake_find_cached)),
        patch("app.services.apify_service.download_bytes", new=AsyncMock(side_effect=fake_download)),
        patch("app.services.thumbnail_service.cache", new=AsyncMock(return_value=CACHED_URL)),
    ):
        await backfill.backfill_thumbnails(batch_size=50)

    assert relinkable.thumbnail_url == CACHED_URL
    assert recacheable.thumbnail_url == CACHED_URL
    # 抓不回來的原樣留著，讓前端走無圖 placeholder，不要留一條死網址以外的假象
    assert unrecoverable.thumbnail_url == "https://dead.cdn/gone.jpg"
    # 第二輪必須帶上游標，否則會重選同一批
    assert get_rows.await_args_list[1].args[3] == unrecoverable.id


async def test_is_cached_url():
    from app.services import thumbnail_service

    assert thumbnail_service.is_cached_url(CACHED_URL)
    assert not thumbnail_service.is_cached_url(PLATFORM_URL)
    assert not thumbnail_service.is_cached_url(None)
