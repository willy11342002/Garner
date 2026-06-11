from uuid import UUID

import httpx
from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import Response

from app.core.config import settings
from app.crud import items as crud_items
from app.crud import locations as crud_locations
from app.dependencies import CurrentUser, DbSession
from app.schemas.location import ContentLocationCreate, ContentLocationRead, ContentLocationUpdate, LocationMapPoint, PlaceCacheRead, PlaceSearchResult
from app.services import ai_service, geocoding_service, place_service

router = APIRouter()


# ── Item-scoped endpoints ──────────────────────────────────────────────────────


@router.get("/items/{item_id}/locations", response_model=list[ContentLocationRead])
async def list_item_locations(item_id: UUID, current_user: CurrentUser, db: DbSession):
    user_id = UUID(current_user["sub"])
    user_item = await crud_items.get_one(db, user_id, item_id)
    if user_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return await crud_locations.list_by_content_id(db, user_item.content_id)


@router.post("/items/{item_id}/locations", response_model=ContentLocationRead, status_code=status.HTTP_201_CREATED)
async def create_item_location(
    item_id: UUID,
    data: ContentLocationCreate,
    current_user: CurrentUser,
    db: DbSession,
):
    user_id = UUID(current_user["sub"])
    user_item = await crud_items.get_one(db, user_id, item_id)
    if user_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    existing = await crud_locations.list_by_content_id(db, user_item.content_id)
    next_order = max((l.order_index for l in existing), default=-1) + 1

    lat, lng = data.lat, data.lng
    if lat is None or lng is None:
        geocode_query = data.geocode_hint or data.name
        lat, lng = await geocoding_service.geocode(geocode_query)

    loc = await crud_locations.create_location(
        db,
        content_id=user_item.content_id,
        name=data.name,
        source="user",
        order_index=next_order,
        lat=lat,
        lng=lng,
    )
    await db.commit()
    await db.refresh(loc)
    return loc


@router.patch(
    "/items/{item_id}/locations/{location_id}",
    response_model=ContentLocationRead,
)
async def update_item_location(
    item_id: UUID,
    location_id: UUID,
    data: ContentLocationUpdate,
    current_user: CurrentUser,
    db: DbSession,
):
    user_id = UUID(current_user["sub"])
    user_item = await crud_items.get_one(db, user_id, item_id)
    if user_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    loc = await crud_locations.get_one(db, location_id)
    if loc is None or loc.content_id != user_item.content_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    updated = await crud_locations.update_location(
        db, location_id, name=data.name
    )
    return updated


@router.delete(
    "/items/{item_id}/locations/{location_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_item_location(
    item_id: UUID,
    location_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
):
    user_id = UUID(current_user["sub"])
    user_item = await crud_items.get_one(db, user_id, item_id)
    if user_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    loc = await crud_locations.get_one(db, location_id)
    if loc is None or loc.content_id != user_item.content_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    await crud_locations.delete_location(db, location_id)


# ── Extract locations for existing item ───────────────────────────────────────


@router.post(
    "/items/{item_id}/locations/extract",
    response_model=list[ContentLocationRead],
)
async def extract_item_locations(
    item_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
):
    """Run AI location extraction on an existing item using stored raw_data.

    Text source priority (same logic as process_item):
    - article : raw_data.text / raw_data.markdown  (full original text)
    - youtube : raw_data.title + raw_data.description
    - ig      : raw_data.caption
    - note    : notes_md (raw_data is empty for internal notes)

    Deletes previous AI-extracted locations, re-extracts, geocodes, and returns results.
    Metadata-sourced locations (IG locationName) are preserved.
    """
    user_id = UUID(current_user["sub"])
    user_item = await crud_items.get_one(db, user_id, item_id)
    if user_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    content_id = user_item.content_id
    raw_data: dict = (user_item.content.raw_data or {}) if user_item.content else {}
    source_type = user_item.source_type

    # Clear old AI-extracted locations; preserve metadata-sourced ones
    await crud_locations.delete_ai_locations(db, content_id)

    # Source 1: IG metadata locationName (mirrors worker logic)
    locations_to_save: list[dict] = []
    metadata_name = raw_data.get("locationName")
    if metadata_name and isinstance(metadata_name, str):
        locations_to_save.append({"name": metadata_name, "order": 0, "source": "metadata"})

    # Source 2: AI extraction from raw_data text
    text = _build_extract_text(raw_data, source_type, user_item.notes_md)
    if text:
        metadata_names = {loc["name"] for loc in locations_to_save}
        ai_locations = await ai_service.extract_locations(text)
        for loc_data in ai_locations:
            name = loc_data.get("name")
            if name and name not in metadata_names:
                locations_to_save.append({"name": name, "order": loc_data.get("order", 0), "source": "ai"})

    if not locations_to_save:
        await db.commit()
        return []

    created = []
    for loc_data in locations_to_save:
        loc_obj = await crud_locations.create_location(
            db,
            content_id=content_id,
            name=loc_data["name"],
            source=loc_data["source"],
            order_index=loc_data.get("order", 0),
        )
        created.append(loc_obj)

    await db.flush()

    for loc_obj in created:
        lat, lng = await geocoding_service.geocode(loc_obj.name)
        loc_obj.lat = lat
        loc_obj.lng = lng

    await db.commit()
    return await crud_locations.list_by_content_id(db, content_id)


def _build_extract_text(
    raw_data: dict,
    source_type: str | None,
    notes_md: str | None,
) -> str:
    """Reconstruct the best available text for location extraction from stored data."""
    if source_type == "article":
        return (raw_data.get("text") or raw_data.get("markdown") or "")[:16000]

    if source_type == "youtube":
        parts: list[str] = []
        title = raw_data.get("title")
        if title:
            parts.append(f"[標題]\n{title}")
        desc = raw_data.get("description") or raw_data.get("text")
        if desc:
            parts.append(f"[說明]\n{desc[:4000]}")
        return "\n\n".join(parts)

    if source_type == "ig":
        return (raw_data.get("caption") or raw_data.get("text") or "")[:4000]

    # note (internal) or unknown: raw_data is empty, fall back to notes_md
    return (notes_md or "")[:8000]


# ── Map bounding box query ─────────────────────────────────────────────────────


@router.get("/locations", response_model=list[LocationMapPoint])
async def get_map_locations(
    current_user: CurrentUser,
    db: DbSession,
    bounds: str = Query(
        description="Comma-separated: sw_lat,sw_lng,ne_lat,ne_lng"
    ),
):
    """Return all geocoded locations within a bounding box for the current user."""
    try:
        parts = [float(p) for p in bounds.split(",")]
        sw_lat, sw_lng, ne_lat, ne_lng = parts
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="bounds must be 'sw_lat,sw_lng,ne_lat,ne_lng'",
        )

    user_id = UUID(current_user["sub"])
    rows = await crud_locations.get_by_bounds(db, user_id, sw_lat, sw_lng, ne_lat, ne_lng)
    return [LocationMapPoint(**row) for row in rows]


# ── Google Places cache ────────────────────────────────────────────────────────
# IMPORTANT: specific routes (/places/photo, /places/lookup) must be declared
# BEFORE the parameterized route (/places/{place_id}) or FastAPI will swallow them.


@router.get("/places/search", response_model=list[PlaceSearchResult])
async def search_places(
    current_user: CurrentUser,
    q: str = Query(min_length=2),
    lat: float | None = Query(default=None, description="Map center latitude — biases results toward this location"),
    lng: float | None = Query(default=None, description="Map center longitude"),
    radius: int = Query(default=5000, ge=500, le=50000, description="Search bias radius in metres"),
):
    """Search places via Google Places Text Search. Returns up to 5 results with coordinates."""
    return await place_service.text_search_places(q, lat=lat, lng=lng, radius=radius)


@router.get("/places/photo")
async def proxy_place_photo(
    ref: str = Query(description="Photo reference name (places/.../photos/...)"),
    max_width: int = Query(default=800, ge=100, le=4096),
):
    """Proxy a Google Places photo so the API key stays server-side. No auth required."""
    if not settings.google_maps_api_key:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Maps API key not configured")

    url = "https://maps.googleapis.com/maps/api/place/photo"
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            resp = await client.get(url, params={"photoreference": ref, "maxwidth": max_width, "key": settings.google_maps_api_key})
        if resp.status_code != 200:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Photo fetch failed")
        return Response(content=resp.content, media_type=resp.headers.get("content-type", "image/jpeg"))
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Photo fetch failed")


@router.get("/places/lookup", response_model=PlaceCacheRead | None)
async def lookup_place_details(
    current_user: CurrentUser,
    db: DbSession,
    name: str = Query(),
    lat: float = Query(),
    lng: float = Query(),
):
    """Find a place by name + coordinates via Google Text Search, return cached details."""
    return await place_service.lookup_place(name, lat, lng, db)


@router.get("/places/{place_id}", response_model=PlaceCacheRead)
async def get_place_details(
    place_id: str,
    current_user: CurrentUser,
    db: DbSession,
):
    """Return cached Google Places details for a place_id (7-day TTL)."""
    result = await place_service.get_place_details(place_id, db)
    if result is None or not result.name:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Place not found")
    return result
