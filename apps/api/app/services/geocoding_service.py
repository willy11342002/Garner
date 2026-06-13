import logging

import httpx

from app.core.config import settings
from app.core.tracing import traced

logger = logging.getLogger(__name__)

GEOCODING_URL = "https://maps.googleapis.com/maps/api/geocode/json"


@traced(op="geocoding", name="geocode")
async def geocode(name: str) -> tuple[float | None, float | None]:
    """Call Google Maps Geocoding API for a place name.

    Returns (lat, lng) on success, (None, None) on failure or missing key.
    """
    if not settings.google_maps_api_key:
        return None, None

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                GEOCODING_URL,
                params={"address": name, "key": settings.google_maps_api_key},
            )
        if resp.status_code != 200:
            logger.warning("Geocoding HTTP %d for %r", resp.status_code, name)
            return None, None

        data = resp.json()
        if data.get("status") != "OK" or not data.get("results"):
            logger.debug("Geocoding no result for %r (status=%s)", name, data.get("status"))
            return None, None

        loc = data["results"][0]["geometry"]["location"]
        return float(loc["lat"]), float(loc["lng"])

    except Exception:
        logger.exception("Geocoding failed for %r", name)
        return None, None
