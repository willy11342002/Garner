import logging
import time
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.crud import places as crud_places
from app.models.place_cache import PlaceCache

logger = logging.getLogger(__name__)

LEGACY_BASE = "https://maps.googleapis.com/maps/api/place"
CACHE_TTL = timedelta(days=7)

_search_cache: dict[str, tuple[str, float]] = {}
_SEARCH_CACHE_SECONDS = 7 * 86400

_DETAIL_FIELDS = "name,rating,reviews,photos,formatted_address,international_phone_number,opening_hours,url"


async def lookup_place(name: str, lat: float, lng: float, db: AsyncSession) -> PlaceCache | None:
    """Find a place by name + coordinates via Text Search, then return cached details."""
    place_id = await _text_search_cached(name, lat, lng)
    if not place_id:
        return None
    return await get_place_details(place_id, db)


async def _text_search_cached(name: str, lat: float, lng: float) -> str | None:
    key = f"{name}:{lat:.3f}:{lng:.3f}"
    cached = _search_cache.get(key)
    if cached and (time.time() - cached[1]) < _SEARCH_CACHE_SECONDS:
        return cached[0]

    place_id = await _text_search(name, lat, lng)
    if place_id:
        _search_cache[key] = (place_id, time.time())
    return place_id


async def _text_search(name: str, lat: float, lng: float) -> str | None:
    if not settings.google_maps_api_key:
        logger.error("Places Text Search: google_maps_api_key is not set")
        return None
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{LEGACY_BASE}/textsearch/json",
                params={
                    "query": name,
                    "location": f"{lat},{lng}",
                    "radius": 500,
                    "key": settings.google_maps_api_key,
                },
            )
        if resp.status_code != 200:
            logger.error("Places Text Search HTTP %d for %r — body: %s", resp.status_code, name, resp.text[:500])
            return None
        data = resp.json()
        results = data.get("results", [])
        if not results:
            logger.info("Places Text Search: no results for %r at (%.4f, %.4f)", name, lat, lng)
            return None
        place_id = results[0].get("place_id")
        logger.info("Places Text Search: found %r → %s", name, place_id)
        return place_id
    except Exception:
        logger.exception("Places Text Search failed for %r", name)
        return None


async def get_place_details(place_id: str, db: AsyncSession) -> PlaceCache:
    cached = await crud_places.get(db, place_id)

    is_stale = (
        cached is None
        or datetime.now(timezone.utc) - cached.cached_at > CACHE_TTL
    )

    if not is_stale:
        return cached

    data = await _fetch_from_google(place_id)
    return await crud_places.upsert(db, place_id, data)


async def _fetch_from_google(place_id: str) -> dict:
    if not settings.google_maps_api_key:
        logger.warning("google_maps_api_key not set")
        return {}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{LEGACY_BASE}/details/json",
                params={
                    "place_id": place_id,
                    "fields": _DETAIL_FIELDS,
                    "key": settings.google_maps_api_key,
                    "language": "zh-TW",
                },
            )
        if resp.status_code != 200:
            logger.error("Places Details HTTP %d for %r — body: %s", resp.status_code, place_id, resp.text[:500])
            return {}
        data = resp.json()
        if data.get("status") not in ("OK", "ZERO_RESULTS"):
            logger.error("Places Details status=%s for %r", data.get("status"), place_id)
            return {}
        return _parse_place(data.get("result", {}))
    except Exception:
        logger.exception("Places Details failed for place_id=%r", place_id)
        return {}


def _parse_place(raw: dict) -> dict:
    reviews = []
    for r in raw.get("reviews", []):
        reviews.append({
            "author": r.get("author_name"),
            "author_photo": r.get("profile_photo_url"),
            "rating": r.get("rating"),
            "text": r.get("text"),
            "relative_time": r.get("relative_time_description"),
            "publish_time": None,
        })

    # Legacy API: photos[].photo_reference (used as the proxy ref param)
    photos = [p["photo_reference"] for p in raw.get("photos", []) if p.get("photo_reference")]

    opening_hours = None
    if raw.get("opening_hours"):
        opening_hours = {
            "open_now": raw["opening_hours"].get("open_now"),
            "weekday_descriptions": raw["opening_hours"].get("weekday_text", []),
        }

    return {
        "name": raw.get("name"),
        "rating": raw.get("rating"),
        "reviews": reviews,
        "photos": photos,
        "address": raw.get("formatted_address"),
        "phone": raw.get("international_phone_number"),
        "opening_hours": opening_hours,
        "maps_url": raw.get("url"),
    }
