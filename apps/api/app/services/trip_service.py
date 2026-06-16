import asyncio
import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import trips as crud_trips
from app.models.trip import Trip, TripItem
from app.schemas.trip import (
    TripCreate,
    TripItemCreate,
    TripItemRead,
    TripItemReorderEntry,
    TripItemTagRead,
    TripItemUpdate,
    TripListItem,
    TripRead,
    TripSourceItem,
    TripUpdate,
)

logger = logging.getLogger(__name__)


def _build_item_read(item: TripItem) -> TripItemRead:
    tags = [
        TripItemTagRead(
            trip_tag_id=it.trip_tag_id,
            name=it.trip_tag.name,
            color=it.trip_tag.color,
        )
        for it in (item.item_tags or [])
    ]
    return TripItemRead(
        id=item.id,
        trip_id=item.trip_id,
        user_item_id=item.user_item_id,
        kind=item.kind,
        title=item.title,
        emoji=item.emoji,
        note=item.note,
        category=item.category,
        booked=item.booked,
        start_date=item.start_date,
        end_date=item.end_date,
        start_time=item.start_time,
        end_time=item.end_time,
        order_index=item.order_index,
        place_name=item.place_name,
        lat=item.lat,
        lng=item.lng,
        geocoding_status=item.geocoding_status,
        tags=tags,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


async def _build_trip_read(db: AsyncSession, user_id: UUID, trip: Trip) -> TripRead:
    sources_raw = await crud_trips.resolve_sources(db, user_id, trip.source_item_ids)
    sources = [
        TripSourceItem(
            id=s.id,
            title=s.title,
            thumbnail_url=s.thumbnail_url,
            source_type=s.source_type,
        )
        for s in sources_raw
    ]
    items = sorted(trip.items or [], key=lambda i: (str(i.start_date) if i.start_date else "", i.order_index))
    return TripRead(
        id=trip.id,
        title=trip.title,
        summary=trip.summary,
        start_date=trip.start_date,
        end_date=trip.end_date,
        last_edited_by=trip.last_edited_by,
        sources=sources,
        items=[_build_item_read(i) for i in items],
        created_at=trip.created_at,
        updated_at=trip.updated_at,
    )


async def list_trips(db: AsyncSession, user_id: UUID) -> list[TripListItem]:
    trips = await crud_trips.list_trips(db, user_id)
    return [
        TripListItem(
            id=t.id,
            title=t.title,
            summary=t.summary,
            start_date=t.start_date,
            end_date=t.end_date,
            source_count=len(t.source_item_ids or []),
            item_count=len(t.items or []),
            last_edited_by=t.last_edited_by,
            created_at=t.created_at,
            updated_at=t.updated_at,
        )
        for t in trips
    ]


async def get_trip(db: AsyncSession, user_id: UUID, trip_id: UUID) -> TripRead | None:
    trip = await crud_trips.get_trip(db, user_id, trip_id)
    if trip is None:
        return None
    return await _build_trip_read(db, user_id, trip)


async def create_trip(
    db: AsyncSession, user_id: UUID, data: TripCreate
) -> TripRead:
    trip = await crud_trips.create_trip(
        db,
        user_id,
        title=data.title,
        summary=data.summary,
        start_date=data.start_date,
        end_date=data.end_date,
        last_edited_by="user",
    )
    trip = await crud_trips.get_trip(db, user_id, trip.id)
    return await _build_trip_read(db, user_id, trip)


async def update_trip(
    db: AsyncSession, user_id: UUID, trip_id: UUID, data: TripUpdate
) -> TripRead | None:
    trip = await crud_trips.get_trip(db, user_id, trip_id)
    if trip is None:
        return None
    trip = await crud_trips.update_trip(
        db,
        trip,
        title=data.title,
        summary=data.summary,
        start_date=data.start_date,
        end_date=data.end_date,
        last_edited_by="user",
    )
    trip = await crud_trips.get_trip(db, user_id, trip.id)
    return await _build_trip_read(db, user_id, trip)


async def delete_trip(db: AsyncSession, user_id: UUID, trip_id: UUID) -> bool:
    trip = await crud_trips.get_trip(db, user_id, trip_id)
    if trip is None:
        return False
    await crud_trips.delete_trip(db, trip)
    return True


# ── TripItem ──────────────────────────────────────────────────────────────────

async def add_item(
    db: AsyncSession, user_id: UUID, trip_id: UUID, data: TripItemCreate
) -> TripItemRead | None:
    trip = await crud_trips.get_trip(db, user_id, trip_id)
    if trip is None:
        return None

    kwargs: dict = dict(
        user_item_id=data.user_item_id,
        kind=data.kind,
        title=data.title,
        emoji=data.emoji,
        note=data.note,
        category=data.category,
        booked=data.booked,
        start_date=data.start_date,
        end_date=data.end_date,
        start_time=data.start_time,
        end_time=data.end_time,
        order_index=data.order_index,
        geocoding_status="done",
    )

    # 繼承來源 item 的地標（優先用 add 傳入的，再 fallback 到 content_location）
    if data.place_name:
        kwargs["place_name"] = data.place_name
        kwargs["lat"] = data.lat
        kwargs["lng"] = data.lng
    elif data.user_item_id:
        loc = await _get_primary_location(db, data.user_item_id)
        if loc:
            kwargs["place_name"] = loc.name
            kwargs["lat"] = loc.lat
            kwargs["lng"] = loc.lng

    item = await crud_trips.create_item(db, trip_id, **kwargs)

    if data.tag_ids:
        from app.models.trip import TripItemTag as _TripItemTag
        for tid in data.tag_ids:
            db.add(_TripItemTag(trip_item_id=item.id, trip_tag_id=tid))
        await db.commit()

    item = await crud_trips.get_item(db, trip_id, item.id)
    return _build_item_read(item)


async def _get_primary_location(db, user_item_id: UUID):
    from sqlalchemy import select
    from app.models.content_location import ContentLocation
    result = await db.execute(
        select(ContentLocation)
        .where(ContentLocation.user_item_id == user_item_id, ContentLocation.lat.isnot(None))
        .order_by(ContentLocation.order_index)
        .limit(1)
    )
    return result.scalar_one_or_none()


async def update_item(
    db: AsyncSession,
    user_id: UUID,
    trip_id: UUID,
    item_id: UUID,
    data: TripItemUpdate,
) -> TripItemRead | None:
    trip = await crud_trips.get_trip(db, user_id, trip_id)
    if trip is None:
        return None
    item = await crud_trips.get_item(db, trip_id, item_id)
    if item is None:
        return None

    update_kwargs = {
        k: v for k, v in data.model_dump(exclude={"tag_ids"}, exclude_unset=True).items()
    }

    # place_name 變更時非同步觸發 geocoding
    trigger_geocode = (
        "place_name" in update_kwargs
        and update_kwargs["place_name"]
        and update_kwargs["place_name"] != item.place_name
        and data.lat is None
    )
    if trigger_geocode:
        update_kwargs["geocoding_status"] = "pending"
        update_kwargs["lat"] = None
        update_kwargs["lng"] = None

    item = await crud_trips.update_item(db, item, tag_ids=data.tag_ids, **update_kwargs)

    if trigger_geocode:
        asyncio.create_task(_geocode_item(db, item.id, update_kwargs["place_name"]))

    item = await crud_trips.get_item(db, trip_id, item_id)
    return _build_item_read(item)


async def _geocode_item(db: AsyncSession, item_id: UUID, place_name: str) -> None:
    from app.services.geocoding_service import geocode
    from sqlalchemy import select, update
    from app.models.trip import TripItem as TripItemModel
    try:
        lat, lng = await geocode(place_name)
        status = "done" if lat else "failed"
        await db.execute(
            update(TripItemModel)
            .where(TripItemModel.id == item_id)
            .values(lat=lat, lng=lng, geocoding_status=status)
        )
        await db.commit()
    except Exception:
        logger.exception("Trip item geocoding failed for item %s", item_id)


async def delete_item(
    db: AsyncSession, user_id: UUID, trip_id: UUID, item_id: UUID
) -> bool:
    trip = await crud_trips.get_trip(db, user_id, trip_id)
    if trip is None:
        return False
    item = await crud_trips.get_item(db, trip_id, item_id)
    if item is None:
        return False
    await crud_trips.delete_item(db, item)
    return True


async def reorder_items(
    db: AsyncSession,
    user_id: UUID,
    trip_id: UUID,
    entries: list[TripItemReorderEntry],
) -> bool:
    trip = await crud_trips.get_trip(db, user_id, trip_id)
    if trip is None:
        return False
    await crud_trips.reorder_items(
        db, [{"id": e.id, "order_index": e.order_index} for e in entries]
    )
    return True
