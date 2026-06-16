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

# category → 標籤顏色，對齊前端 trips.vue 建立的預設標籤（同名會被 get_or_create_tag 沿用）
_CATEGORY_TAG_COLORS = {"景點": "d", "美食": "e", "交通": "b", "住宿": "a"}


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


async def create_trip_from_chat(
    db: AsyncSession,
    user_id: UUID,
    *,
    title: str,
    summary: str | None = None,
    start_date=None,
    end_date=None,
    cards: list[dict] | None = None,
    source_item_ids: list | None = None,
) -> dict:
    """chat 的 create_trip 工具用：LLM 已規劃好行程，這裡持久化成結構化 trip + 每日卡片。
    有 place_name 的卡片在背景做 geocoding 以便地圖定位。回傳精簡 dict 給 chat 卡片。"""
    from datetime import date as _date, datetime as _dt, timedelta

    def _parse_date(v):
        if v is None or not isinstance(v, str):
            return v
        try:
            return _date.fromisoformat(v)
        except Exception:
            return None

    def _parse_time(v):
        if not v or not isinstance(v, str):
            return None
        try:
            return _dt.strptime(v, "%H:%M").time()
        except Exception:
            return None

    sd = _parse_date(start_date)
    ed = _parse_date(end_date)

    trip = await crud_trips.create_trip(
        db, user_id,
        title=title, summary=summary,
        start_date=sd, end_date=ed,
        source_item_ids=source_item_ids,
        last_edited_by="ai",
    )

    pending_geocode: list[tuple[UUID, str]] = []
    cards = cards or []
    for idx, card in enumerate(cards):
        place = (card.get("place_name") or "").strip() or None
        # day（1 起算）+ trip 起始日 → 推算該卡片日期（沒起始日就留空）
        item_date = None
        day = card.get("day")
        if sd and isinstance(day, int) and day >= 1:
            item_date = sd + timedelta(days=day - 1)
        item = await crud_trips.create_item(
            db, trip.id,
            kind="event",
            title=(card.get("title") or "未命名").strip(),
            emoji=(card.get("emoji") or None),
            note=(card.get("note") or None),
            category=(card.get("category") or None),
            booked=False,
            start_date=item_date,
            start_time=_parse_time(card.get("start_time")),
            order_index=float(idx),
            place_name=place,
            geocoding_status=("pending" if place else "done"),
        )
        if place:
            pending_geocode.append((item.id, place))

    if pending_geocode:
        asyncio.create_task(_geocode_items_bg(pending_geocode))

    return {
        "id": str(trip.id),
        "title": trip.title,
        "summary": trip.summary,
        "item_count": len(cards),
    }


async def add_card_from_chat(
    db: AsyncSession,
    user_id: UUID,
    trip_id: UUID,
    *,
    day=None,
    title: str = "未命名",
    place_name: str | None = None,
    category: str | None = None,
    emoji: str | None = None,
    start_time=None,
    note: str | None = None,
) -> dict | None:
    """chat 的 add_trip_card 工具用：對既有行程逐張新增卡片，回傳精簡 dict。"""
    from datetime import datetime as _dt, timedelta
    from urllib.parse import quote

    trip = await crud_trips.get_trip(db, user_id, trip_id)
    if trip is None:
        return None

    def _parse_time(v):
        if not v or not isinstance(v, str):
            return None
        try:
            return _dt.strptime(v, "%H:%M").time()
        except Exception:
            return None

    # day 可能以 int / "1" / 1.0 等形式傳來，統一轉成 int 再算日期
    day_int = None
    try:
        day_int = int(day) if day is not None else None
    except (ValueError, TypeError):
        day_int = None
    item_date = None
    if trip.start_date and day_int and day_int >= 1:
        item_date = trip.start_date + timedelta(days=day_int - 1)

    # place_name 欄位前端當「可點的地圖連結」用，所以把純地名轉成 Google Maps 連結；
    # geocoding 仍用原始地名取座標（地圖標點靠 lat/lng，不靠這個連結）。
    raw_place = (place_name or "").strip() or None
    geocode_query = None
    stored_place = None
    if raw_place:
        if raw_place.startswith("http"):
            stored_place = raw_place  # 模型已給連結，直接用（無法 geocode）
        else:
            stored_place = f"https://www.google.com/maps/search/?api=1&query={quote(raw_place)}"
            geocode_query = raw_place

    item = await crud_trips.create_item(
        db, trip_id,
        kind="event",
        title=(title or "未命名").strip()[:60],  # 防呆：title 過長截斷，避免整段敘述塞進標題
        emoji=(emoji or None),
        note=(note or None),
        category=(category or None),
        booked=False,
        start_date=item_date,
        start_time=_parse_time(start_time),
        order_index=float(len(trip.items or [])),  # 接在現有卡片之後
        place_name=stored_place,
        geocoding_status=("pending" if geocode_query else "done"),
    )

    # category（景點／美食／交通／住宿）對應成 trip 標籤並掛到卡片，否則 board 視圖會全擠在「無標籤」。
    # 卡片已建立成功，標籤掛失敗不該讓整張卡視為失敗，故獨立 try。
    cat = (category or "").strip()
    if cat in _CATEGORY_TAG_COLORS:
        try:
            from app.models.trip import TripItemTag as _TripItemTag
            tag = await crud_trips.get_or_create_tag(db, user_id, cat, _CATEGORY_TAG_COLORS[cat])
            db.add(_TripItemTag(trip_item_id=item.id, trip_tag_id=tag.id))
            await db.commit()
        except Exception:
            logger.exception("attach category tag failed for item %s", item.id)

    if geocode_query:
        asyncio.create_task(_geocode_items_bg([(item.id, geocode_query)]))
    return {"ok": True, "title": item.title}


async def _geocode_items_bg(items: list[tuple[UUID, str]]) -> None:
    """背景批次 geocoding：開自己的 session（不共用 request session，避免並發/生命週期問題）。"""
    from app.core.database import AsyncSessionLocal
    from app.services.geocoding_service import geocode
    from sqlalchemy import update
    from app.models.trip import TripItem as TripItemModel
    async with AsyncSessionLocal() as db:
        for item_id, place_name in items:
            try:
                lat, lng = await geocode(place_name)
                status = "done" if lat else "failed"
                await db.execute(
                    update(TripItemModel).where(TripItemModel.id == item_id)
                    .values(lat=lat, lng=lng, geocoding_status=status)
                )
                await db.commit()
            except Exception:
                logger.exception("trip item geocoding failed for item %s", item_id)


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
