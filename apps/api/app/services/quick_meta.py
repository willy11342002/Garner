"""Synchronous, lightweight metadata fetch used before item creation.

Runs inline in the POST /items/ request (blocking the response) so title /
thumbnail are already correct on first paint, instead of waiting for the full
background ingest pipeline. Never raises — on failure/timeout the caller
downgrades the response to 203 and the background pipeline still fetches
everything properly, so `title` ends up correct either way.

YouTube / TikTok use each platform's public oEmbed endpoint (no credentials,
no Apify call).

Instagram / Facebook have no public oEmbed (Meta's official oEmbed requires
an App Review-gated access token this project doesn't have), but their post
pages serve fully server-rendered Open Graph tags (og:title/og:description/
og:image) to Meta's own link-preview crawler — recognized by the
`facebookexternalhit` User-Agent, which bypasses the login/JS wall regular
requests hit. ~1-2s per request, no Apify call at all. Same trick messaging
apps (Slack/Messenger/Discord) use to render link previews for public posts.

Article reuses the existing single Apify call, which also yields the full
text, so the background pipeline's fetch node ends up a no-op for it.
"""
import asyncio
import html
import logging
import re
from dataclasses import dataclass, field

import httpx

logger = logging.getLogger(__name__)

_TIMEOUT_SEC = 8.0
_OG_USER_AGENT = "facebookexternalhit/1.1"
_TITLE_MAX_LEN = 20


@dataclass
class QuickMeta:
    ok: bool
    title: str | None = None
    thumbnail_url: str | None = None
    duration_sec: int | None = None
    raw_data: dict = field(default_factory=dict)
    # Only populated for "article" — the same Apify call already yields the
    # full text, so the background fetch node can skip re-fetching entirely.
    raw_content: str | None = None


async def fetch(source_type: str, url: str, content_id: str) -> QuickMeta:
    try:
        if source_type == "youtube":
            return await asyncio.wait_for(
                _oembed("https://www.youtube.com/oembed", url), timeout=_TIMEOUT_SEC
            )
        if source_type == "tiktok":
            return await asyncio.wait_for(
                _oembed("https://www.tiktok.com/oembed", url), timeout=_TIMEOUT_SEC
            )
        if source_type == "ig":
            return await asyncio.wait_for(_og_scrape_ig(url), timeout=_TIMEOUT_SEC)
        if source_type in ("facebook_reel", "facebook_post"):
            return await asyncio.wait_for(_og_scrape_facebook(url), timeout=_TIMEOUT_SEC)
        if source_type == "article":
            return await asyncio.wait_for(
                _provider_fetch_info(source_type, url, content_id), timeout=_TIMEOUT_SEC
            )
    except Exception:
        logger.warning(
            "quick_meta failed: source_type=%s url=%s", source_type, url, exc_info=True
        )
    return QuickMeta(ok=False)


async def _oembed(endpoint: str, url: str) -> QuickMeta:
    async with httpx.AsyncClient(timeout=_TIMEOUT_SEC) as client:
        resp = await client.get(endpoint, params={"url": url, "format": "json"})
        resp.raise_for_status()
        data = resp.json()
    return QuickMeta(
        ok=True,
        title=data.get("title"),
        thumbnail_url=data.get("thumbnail_url"),
    )


async def _fetch_og_tags(url: str) -> dict[str, str | None]:
    async with httpx.AsyncClient(timeout=_TIMEOUT_SEC, follow_redirects=True) as client:
        resp = await client.get(url, headers={"User-Agent": _OG_USER_AGENT})
        resp.raise_for_status()
        page = resp.text

    def _extract(prop: str) -> str | None:
        m = re.search(rf'<meta property="{re.escape(prop)}" content="([^"]*)"', page)
        return html.unescape(m.group(1)) if m else None

    return {
        "title": _extract("og:title"),
        "description": _extract("og:description"),
        "image": _extract("og:image"),
    }


def _short_title(text: str | None) -> str | None:
    if not text:
        return None
    first_line = text.strip().splitlines()[0] if text.strip() else ""
    return first_line[:_TITLE_MAX_LEN] or None


async def _og_scrape_ig(url: str) -> QuickMeta:
    tags = await _fetch_og_tags(url)
    # og:title looks like `{account} on Instagram: "{caption}"` — pull the
    # quoted caption out; same first-line/20-char convention as the full
    # provider (providers/instagram.py) uses once the real Apify fetch runs.
    caption_match = re.search(r'on Instagram:\s*"(.*)"\s*$', tags["title"] or "", re.DOTALL)
    caption = caption_match.group(1) if caption_match else tags["title"]
    return QuickMeta(ok=True, title=_short_title(caption), thumbnail_url=tags["image"])


async def _og_scrape_facebook(url: str) -> QuickMeta:
    tags = await _fetch_og_tags(url)
    # og:description is just the post text, without the view/reaction-count
    # and page-name noise og:title carries — prefer it when present.
    caption = tags["description"] or tags["title"]
    return QuickMeta(ok=True, title=_short_title(caption), thumbnail_url=tags["image"])


async def _provider_fetch_info(source_type: str, url: str, content_id: str) -> QuickMeta:
    from app.providers import get_provider

    provider = get_provider(url)
    info = await provider.fetch_info(url, content_id)

    raw_content = info.raw_content
    if source_type == "article" and raw_content is None:
        # DefaultProvider derives text purely from the already-fetched
        # raw_data — no extra network call, safe to run inline here too.
        raw_content = await provider.fetch_content(url, info)

    return QuickMeta(
        ok=True,
        title=info.title,
        thumbnail_url=info.thumbnail_url,
        duration_sec=info.duration_sec,
        raw_data=info.raw_data,
        raw_content=raw_content,
    )
