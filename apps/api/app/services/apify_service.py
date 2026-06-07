import asyncio
import logging
from dataclasses import dataclass, field

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_YT_ACTOR = "streamers/youtube-scraper"
_IG_ACTOR = "apify/instagram-scraper"
_WEB_ACTOR = "apify/website-content-crawler"
_DOWNLOAD_TIMEOUT = 60


@dataclass
class ApifyMediaResult:
    raw_data: dict
    title: str | None = None
    description: str | None = None
    duration_sec: int | None = None
    thumbnail_url: str | None = None
    video_urls: list[str] = field(default_factory=list)
    image_urls: list[str] = field(default_factory=list)


@dataclass
class ApifyArticleResult:
    raw_data: dict
    title: str | None = None
    text: str | None = None
    thumbnail_url: str | None = None


def _run_actor(actor_id: str, run_input: dict) -> list[dict]:
    """Synchronous Apify actor call — wrap in asyncio.to_thread()."""
    from apify_client import ApifyClient

    client = ApifyClient(settings.apify_api_token)
    run = client.actor(actor_id).call(run_input=run_input, timeout_secs=180)
    if not run:
        return []
    return list(client.dataset(run["defaultDatasetId"]).iterate_items())


async def fetch_youtube(url: str) -> ApifyMediaResult:
    run_input = {"startUrls": [{"url": url}], "maxResults": 1}
    try:
        items = await asyncio.to_thread(_run_actor, _YT_ACTOR, run_input)
    except Exception:
        logger.exception("Apify YouTube scraper failed for url=%s", url)
        return ApifyMediaResult(raw_data={})

    if not items:
        return ApifyMediaResult(raw_data={})

    item = items[0]
    video_url = item.get("videoUrl") or item.get("streamUrl")

    return ApifyMediaResult(
        raw_data=item,
        title=item.get("title"),
        description=item.get("description") or item.get("text"),
        duration_sec=_parse_duration(item.get("duration")),
        thumbnail_url=item.get("thumbnailUrl"),
        video_urls=[video_url] if video_url else [],
        image_urls=[],
    )


async def fetch_instagram(url: str) -> ApifyMediaResult:
    run_input = {"directUrls": [url], "resultsType": "posts", "resultsLimit": 1}
    try:
        items = await asyncio.to_thread(_run_actor, _IG_ACTOR, run_input)
    except Exception:
        logger.exception("Apify Instagram scraper failed for url=%s", url)
        return ApifyMediaResult(raw_data={})

    if not items:
        return ApifyMediaResult(raw_data={})

    item = items[0]
    image_urls, video_urls, duration_sec = _extract_ig_media(item)

    thumbnail_url = (
        image_urls[0] if image_urls
        else item.get("displayUrl")
        or item.get("thumbnailUrl")
    )

    return ApifyMediaResult(
        raw_data=item,
        title=None,
        description=item.get("caption") or item.get("text"),
        duration_sec=duration_sec or None,
        thumbnail_url=thumbnail_url,
        video_urls=video_urls,
        image_urls=image_urls,
    )


async def fetch_article(url: str) -> ApifyArticleResult:
    run_input = {
        "startUrls": [{"url": url}],
        "maxCrawlPages": 1,
        "crawlerType": "cheerio",
    }
    try:
        items = await asyncio.to_thread(_run_actor, _WEB_ACTOR, run_input)
    except Exception:
        logger.exception("Apify web crawler failed for url=%s", url)
        return ApifyArticleResult(raw_data={})

    if not items:
        return ApifyArticleResult(raw_data={})

    item = items[0]
    return ApifyArticleResult(
        raw_data=item,
        title=item.get("title"),
        text=item.get("text") or item.get("markdown"),
        thumbnail_url=item.get("screenshotUrl"),
    )


async def download_bytes(url: str) -> bytes | None:
    """Download bytes from a CDN URL into memory."""
    try:
        async with httpx.AsyncClient(timeout=_DOWNLOAD_TIMEOUT, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
            return resp.content
    except Exception:
        logger.warning("download_bytes failed url=%s", url, exc_info=True)
        return None


# ── Internal helpers ────────────────────────────────────────────────────────────

def _extract_ig_media(item: dict) -> tuple[list[str], list[str], int]:
    """Return (image_urls, video_urls, total_duration_sec) from an IG scraper item."""
    image_urls: list[str] = []
    video_urls: list[str] = []
    duration_sec = 0

    sidecars = item.get("sidecars") or item.get("childPosts") or []
    if sidecars:
        for node in sidecars:
            if node.get("videoUrl"):
                video_urls.append(node["videoUrl"])
                duration_sec += int(node.get("videoDuration") or 0)
            elif node.get("displayUrl"):
                image_urls.append(node["displayUrl"])
    else:
        if item.get("videoUrl"):
            video_urls.append(item["videoUrl"])
            duration_sec = int(item.get("videoDuration") or 0)
        elif item.get("displayUrl"):
            image_urls.append(item["displayUrl"])

    return image_urls, video_urls, duration_sec


def _parse_duration(value) -> int | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        parts = value.split(":")
        try:
            if len(parts) == 3:
                h, m, s = parts
                return int(h) * 3600 + int(m) * 60 + int(s)
            if len(parts) == 2:
                m, s = parts
                return int(m) * 60 + int(s)
            return int(value)
        except ValueError:
            return None
    return None
