from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content_location import ContentLocation
from app.models.user_item import UserItem, UserItemStatus


async def list_by_user_item_id(db: AsyncSession, user_item_id: UUID) -> list[ContentLocation]:
    result = await db.execute(
        select(ContentLocation)
        .where(ContentLocation.user_item_id == user_item_id)
        .order_by(ContentLocation.order_index)
    )
    return list(result.scalars().all())


async def get_one(db: AsyncSession, location_id: UUID) -> ContentLocation | None:
    result = await db.execute(
        select(ContentLocation).where(ContentLocation.id == location_id)
    )
    return result.scalar_one_or_none()


async def create_location(
    db: AsyncSession,
    user_item_id: UUID,
    name: str,
    source: str,
    order_index: int,
    lat: float | None = None,
    lng: float | None = None,
    geocoding_status: str = "done",
) -> ContentLocation:
    loc = ContentLocation(
        user_item_id=user_item_id,
        name=name,
        source=source,
        order_index=order_index,
        lat=lat,
        lng=lng,
        geocoding_status=geocoding_status,
    )
    db.add(loc)
    return loc


async def update_geocoding_status(
    db: AsyncSession,
    location_id: UUID,
    status: str,
    lat: float | None = None,
    lng: float | None = None,
) -> None:
    loc = await get_one(db, location_id)
    if loc is None:
        return
    loc.geocoding_status = status
    if lat is not None:
        loc.lat = lat
    if lng is not None:
        loc.lng = lng


async def update_lat_lng(
    db: AsyncSession, location_id: UUID, lat: float | None, lng: float | None
) -> None:
    loc = await get_one(db, location_id)
    if loc is not None:
        loc.lat = lat
        loc.lng = lng


async def update_location(
    db: AsyncSession,
    location_id: UUID,
    name: str | None = None,
) -> ContentLocation | None:
    loc = await get_one(db, location_id)
    if loc is None:
        return None
    if name is not None:
        loc.name = name
    await db.commit()
    await db.refresh(loc)
    return loc


async def delete_location(db: AsyncSession, location_id: UUID) -> bool:
    loc = await get_one(db, location_id)
    if loc is None:
        return False
    await db.delete(loc)
    await db.commit()
    return True


async def delete_ai_locations(db: AsyncSession, user_item_id: UUID) -> None:
    from sqlalchemy import delete as sql_delete
    await db.execute(
        sql_delete(ContentLocation).where(
            ContentLocation.user_item_id == user_item_id,
            ContentLocation.source == "ai",
        )
    )


async def get_by_bounds(
    db: AsyncSession,
    user_id: UUID,
    sw_lat: float,
    sw_lng: float,
    ne_lat: float,
    ne_lng: float,
) -> list[dict]:
    """Return all geocoded locations within the bounding box for a user."""
    rows = (
        await db.execute(
            select(ContentLocation, UserItem)
            .join(UserItem, ContentLocation.user_item_id == UserItem.id)
            .where(
                UserItem.user_id == user_id,
                UserItem.deleted_at.is_(None),
                UserItem.status == UserItemStatus.active,
                ContentLocation.lat.isnot(None),
                ContentLocation.lng.isnot(None),
                ContentLocation.lat.between(sw_lat, ne_lat),
                ContentLocation.lng.between(sw_lng, ne_lng),
            )
        )
    ).all()

    return [
        {
            "id": loc.id,
            "name": loc.name,
            "lat": loc.lat,
            "lng": loc.lng,
            "source": loc.source,
            "item_id": item.id,
            "item_title": item.title,
            "item_thumbnail": item.thumbnail_url,
            "item_source_type": item.source_type,
        }
        for loc, item in rows
    ]
