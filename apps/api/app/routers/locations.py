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
from app.quota_depends import ReanalyzeQuota
from app.schemas.location import ContentLocationCreate, ContentLocationRead, ContentLocationUpdate, ExtractLocationsResponse, LocationMapPoint, PlaceCacheRead, PlaceSearchResult
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
        for loc_id, name, (lat, lng) in zip(location_ids, names, results):
            final_status = "done" if lat is not None else "failed"
            await crud_locations.update_geocoding_status(db, loc_id, status=final_status, lat=lat, lng=lng)
        await db.commit()


@router.post(
    "/items/{item_id}/locations/extract",
    response_model=ExtractLocationsResponse,
)
async def extract_item_locations(
    item_id: UUID,
    background_tasks: BackgroundTasks,
    current_user: CurrentUser,
    db: DbSession,
    _quota: ReanalyzeQuota,
):
    """Re-run location extraction for an existing item.

    Consumes one monthly save quota (ReanalyzeQuota checks + increments before
    this body runs). Deletes existing AI and metadata locations, then reruns
    the landmarks pipeline stage in the background. Always returns immediately
    with extracting=True so the frontend can poll until locations appear.
    """
    user_id = UUID(current_user["sub"])
    user_item = await crud_items.get_one(db, user_id, item_id)
    if user_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    async def _run_landmarks() -> None:
        from sqlalchemy import select
        from app.models.user_item import UserItem
        from app.workers.process_item import _stage_landmarks
        from app.services import ai_service

        lm_item_id = user_item.id
        async with AsyncSessionLocal() as bg_db:
            await crud_locations.delete_auto_locations(bg_db, lm_item_id)
            await bg_db.commit()
            notes_md = (await bg_db.execute(
                select(UserItem.notes_md).where(UserItem.id == lm_item_id)
            )).scalar_one() or ""

        # _stage_landmarks opens its own session internally.
        ai_locations = await ai_service.extract_locations(notes_md)
        await _stage_landmarks(lm_item_id, ai_locations)

    background_tasks.add_task(_run_landmarks)
    current_locs = await crud_locations.list_by_user_item_id(db, user_item.id)
    return ExtractLocationsResponse(locations=current_locs, extracting=True)


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
