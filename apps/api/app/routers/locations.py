import asyncio
from uuid import UUID

import httpx
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.crud import items as crud_items
from app.crud import locations as crud_locations
from app.dependencies import CurrentUser, DbSession
from app.schemas.location import ContentLocationCreate, ContentLocationRead, ContentLocationUpdate, LocationMapPoint, PlaceCacheRead, PlaceSearchResult
from app.services import geocoding_service, place_service

router = APIRouter()


# ── Item-scoped endpoints ──────────────────────────────────────────────────────


@router.get("/items/{item_id}/locations", response_model=list[ContentLocationRead])
async def list_item_locations(item_id: UUID, current_user: CurrentUser, db: DbSession):
    user_id = UUID(current_user["sub"])
    user_item = await crud_items.get_one(db, user_id, item_id)
    if user_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return await crud_locations.list_by_user_item_id(db, user_item.id)


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

    existing = await crud_locations.list_by_user_item_id(db, user_item.id)
    next_order = max((l.order_index for l in existing), default=-1) + 1

    lat, lng = data.lat, data.lng
    if lat is None or lng is None:
        geocode_query = data.geocode_hint or data.name
        lat, lng = await geocoding_service.geocode(geocode_query)

    loc = await crud_locations.create_location(
        db,
        user_item_id=user_item.id,
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
    if loc is None or loc.user_item_id != user_item.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    updated = await crud_locations.update_location(db, location_id, name=data.name)
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
    if loc is None or loc.user_item_id != user_item.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    await crud_locations.delete_location(db, location_id)


# ── Extract locations for existing item ───────────────────────────────────────


async def _geocode_locations_bg(location_ids: list[UUID], names: list[str]) -> None:
    """Geocode a batch of locations in the background using a fresh DB session."""
    async with AsyncSessionLocal() as db:
        results = await asyncio.gather(*[geocoding_service.geocode(name) for name in names])
        for loc_id, (lat, lng) in zip(location_ids, results):
            loc = await crud_locations.get_one(db, loc_id)
            if loc is not None:
                loc.lat = lat
                loc.lng = lng
        await db.commit()


@router.post(
    "/items/{item_id}/locations/extract",
    response_model=list[ContentLocationRead],
)
async def extract_item_locations(
    item_id: UUID,
    background_tasks: BackgroundTasks,
    current_user: CurrentUser,
    db: DbSession,
):
    """Re-run location extraction for an existing item.

    Saves locations immediately (lat/lng may be null) and geocodes in the background
    so the response always returns within a few seconds.
    """
    user_id = UUID(current_user["sub"])
    user_item = await crud_items.get_one(db, user_id, item_id)
    if user_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    if user_item.extract is None:
        # Legacy item: re-run the full pipeline in the background, return current locations
        from app.workers.process_item import process_item as _process_item
        async def _run_legacy() -> None:
            async with AsyncSessionLocal() as bg_db:
                await _process_item(bg_db, user_id, user_item.id, user_item.url)
        background_tasks.add_task(_run_legacy)
        return await crud_locations.list_by_user_item_id(db, user_item.id)

    # Has extract snapshot: rebuild from stored data
    extract: dict = user_item.extract
    raw_data: dict = user_item.raw_data or {}

    await crud_locations.delete_ai_locations(db, user_item.id)

    locations_to_save: list[dict] = []

    metadata_name = raw_data.get("locationName")
    if metadata_name and isinstance(metadata_name, str):
        locations_to_save.append({"name": metadata_name, "order": 0, "source": "metadata"})

    metadata_names = {loc["name"] for loc in locations_to_save}
    for loc in extract.get("locations", []):
        name = loc.get("name")
        if name and name not in metadata_names:
            locations_to_save.append({"name": name, "order": loc.get("order", 0), "source": "ai"})

    if not locations_to_save:
        await db.commit()
        return []

    created = []
    for loc_data in locations_to_save:
        loc_obj = await crud_locations.create_location(
            db,
            user_item_id=user_item.id,
            name=loc_data["name"],
            source=loc_data["source"],
            order_index=loc_data.get("order", 0),
        )
        created.append(loc_obj)

    await db.commit()

    # Geocode in background — response returns immediately with null lat/lng
    background_tasks.add_task(
        _geocode_locations_bg,
        [loc.id for loc in created],
        [loc.name for loc in created],
    )

    return await crud_locations.list_by_user_item_id(db, user_item.id)


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


@router.get("/places/search", response_model=list[PlaceSearchResult])
async def search_places(
    current_user: CurrentUser,
    q: str = Query(min_length=2),
    lat: float | None = Query(default=None),
    lng: float | None = Query(default=None),
    radius: int = Query(default=5000, ge=500, le=50000),
):
    return await place_service.text_search_places(q, lat=lat, lng=lng, radius=radius)


@router.get("/places/photo")
async def proxy_place_photo(
    ref: str = Query(description="Photo reference name (places/.../photos/...)"),
    max_width: int = Query(default=800, ge=100, le=4096),
):
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
    return await place_service.lookup_place(name, lat, lng, db)


@router.get("/places/{place_id}", response_model=PlaceCacheRead)
async def get_place_details(
    place_id: str,
    current_user: CurrentUser,
    db: DbSession,
):
    result = await place_service.get_place_details(place_id, db)
    if result is None or not result.name:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Place not found")
    return result
