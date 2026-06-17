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

# 卡片關聯知識的對照表型別：user_item_id → 已解析的來源資訊
SourceMap = dict[UUID, TripSourceItem]

logger = logging.getLogger(__name__)

# category → 標籤顏色，對齊前端 trips.vue 建立的預設標籤（同名會被 get_or_create_tag 沿用）
_CATEGORY_TAG_COLORS = {"景點": "d", "美食": "e", "交通": "b", "住宿": "a"}


def _build_item_read(item: TripItem, source_map: SourceMap | None = None) -> TripItemRead:
    tags = [
        TripItemTagRead(
            trip_tag_id=it.trip_tag_id,
            name=it.trip_tag.name,
            color=it.trip_tag.color,
        )
        for it in (item.item_tags or [])
    ]
    # 依卡片的 sources（user_item_id）查對照表，組出可顯示的關聯知識
    sources: list[TripSourceItem] = []
    if source_map:
        for s in (item.sources or []):
            resolved = source_map.get(s.user_item_id)
            if resolved is not None:
                sources.append(resolved)
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
        ticket_url=item.ticket_url,
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
        sources=sources,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


async def _build_item_source_map(
    db: AsyncSession, user_id: UUID, items: list[TripItem]
) -> SourceMap:
    """一次解析一批 items 用到的所有關聯知識（避免 N+1）。"""
    all_ids: list[UUID] = []
    seen: set[UUID] = set()
    for it in items:
        for s in (it.sources or []):
            if s.user_item_id not in seen:
                seen.add(s.user_item_id)
                all_ids.append(s.user_item_id)
    if not all_ids:
        return {}
    resolved = await crud_trips.resolve_sources(db, user_id, all_ids)
    return {
        ui.id: TripSourceItem(
            id=ui.id,
            title=ui.title,
            thumbnail_url=ui.thumbnail_url,
            source_type=ui.source_type,
        )
        for ui in resolved
    }


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
    source_map = await _build_item_source_map(db, user_id, items)
    return TripRead(
        id=trip.id,
        title=trip.title,
        summary=trip.summary,
        start_date=trip.start_date,
        end_date=trip.end_date,
        last_edited_by=trip.last_edited_by,
        sources=sources,
        items=[_build_item_read(i, source_map) for i in items],
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
    end_day=None,
    title: str = "未命名",
    place_name: str | None = None,
    category: str | None = None,
    emoji: str | None = None,
    start_time=None,
    note: str | None = None,
    ticket_url: str | None = None,
    source_item_ids: list[str] | None = None,
) -> dict | None:
    """chat 的 add_trip_card 工具用：對既有行程逐張新增卡片，回傳精簡 dict。
    source_item_ids：依地點對應到的知識 user_item id（已在上游用 seen_ids 過濾），寫入關聯表。"""
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
    def _to_int(v):
        try:
            return int(v) if v is not None else None
        except (ValueError, TypeError):
            return None

    day_int = _to_int(day)
    item_date = None
    if trip.start_date and day_int and day_int >= 1:
        item_date = trip.start_date + timedelta(days=day_int - 1)

    # end_day → end_date（跨日卡片，例如住宿前三天某飯店）。需 >= day 才視為有效 span
    end_day_int = _to_int(end_day)
    end_item_date = None
    if trip.start_date and end_day_int and end_day_int >= (day_int or 1):
        end_item_date = trip.start_date + timedelta(days=end_day_int - 1)

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
        end_date=end_item_date,
        start_time=_parse_time(start_time),
        order_index=float(len(trip.items or [])),  # 接在現有卡片之後
        place_name=stored_place,
        ticket_url=((ticket_url or "").strip() or None),
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

    # 知識關聯（依地點對應的知識 item）。寫失敗不影響卡片本身，故獨立 try。
    parsed_sources = _parse_uuid_list(source_item_ids)
    if parsed_sources:
        try:
            await crud_trips.set_item_sources(db, item.id, parsed_sources)
        except Exception:
            logger.exception("attach sources failed for item %s", item.id)

    if geocode_query:
        asyncio.create_task(_geocode_items_bg([(item.id, geocode_query)]))
    return {"ok": True, "id": str(item.id), "title": item.title}


def _parse_uuid_list(values: list[str] | None) -> list[UUID]:
    """把字串 id 清單轉成 UUID，解析失敗者略過。"""
    out: list[UUID] = []
    for v in values or []:
        try:
            out.append(v if isinstance(v, UUID) else UUID(str(v)))
        except (ValueError, TypeError):
            continue
    return out


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
        ticket_url=data.ticket_url,
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
    source_map = await _build_item_source_map(db, user_id, [item])
    return _build_item_read(item, source_map)


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
    source_map = await _build_item_source_map(db, user_id, [item])
    return _build_item_read(item, source_map)


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


# ── AI 修改既有行程 ──────────────────────────────────────────────────────────────

_TRIP_EDIT_SYSTEM = """\
你是 Garner 的旅遊行程編輯助理。用戶有一份「既有」的旅遊行程，會給你修改指示。
你的工作是依指示，用工具對這份行程的卡片做「新增／修改／刪除」，把行程調整到位。

規則：
- 只能用工具改動行程，不要把行程內容用文字重貼一遍
- 新增景點／餐廳／交通／住宿：用 add_card，一個地點一張卡，title 只放名稱（≤20 字），細節放 note
- 修改某張卡片：用 update_card，card_no 用下方「目前卡片」清單的編號；只填要改的欄位
- 刪除某張卡片：用 delete_card，card_no 用清單編號
- 一次指示可呼叫多個工具（例如新增好幾張卡、或同時改多張）
- place_name 只放純地點名稱（含城市，例如「大阪 道頓堀」），用於地圖定位，不要放網址
- 用戶提供票券／訂位網址，或要你補上票券連結時，用 ticket_url 帶上完整網址（與地標 place_name 是不同欄位，網址放這裡）
- 跨日的卡片（住宿連住數晚、租車多日、多日票券）要帶 end_day：例如「前 3 天住 A 飯店、後 2 天住 B 飯店」就建兩張住宿卡，A 卡 day=1/end_day=3、B 卡 day=4/end_day=5
- 全部改完後，用繁體中文寫 1～2 句話簡短說明你做了哪些調整
- 若指示與行程編輯無關，簡短說明你只能幫忙編輯這份行程的卡片
"""

_TRIP_EDIT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "add_card",
            "description": "在這份行程新增一張卡片（單一景點／餐廳／交通／住宿）。需要幾個點就呼叫幾次。",
            "parameters": {
                "type": "object",
                "properties": {
                    "day": {"type": "integer", "description": "第幾天，從 1 開始（行程有起始日才會排到該天）"},
                    "end_day": {"type": "integer", "description": "跨日卡片的結束日（含當天，從 1 開始）。單日項目不用填；住宿／租車／多日票等才填，例如住前 3 天 day=1、end_day=3"},
                    "title": {"type": "string", "maxLength": 30, "description": "卡片名稱：單一景點／餐廳／活動，簡短（≤20 字）"},
                    "place_name": {"type": "string", "description": "純地點名稱（含城市，例如「大阪 道頓堀」），用於地圖定位，不要放網址"},
                    "category": {"type": "string", "enum": ["景點", "美食", "交通", "住宿"], "description": "分類，可選"},
                    "emoji": {"type": "string", "description": "代表性 emoji，可選"},
                    "start_time": {"type": "string", "description": "建議時間 HH:MM，可選"},
                    "note": {"type": "string", "description": "卡片細節（玩法、交通、提醒等），markdown 格式，可選"},
                    "ticket_url": {"type": "string", "description": "票券／訂位連結（完整網址），可選"},
                },
                "required": ["title"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_card",
            "description": "修改一張既有卡片。card_no 用「目前卡片」清單的編號。只填要變更的欄位，未填的保持不變。",
            "parameters": {
                "type": "object",
                "properties": {
                    "card_no": {"type": "integer", "description": "要修改的卡片編號（見「目前卡片」清單）"},
                    "day": {"type": "integer", "description": "改成第幾天，從 1 開始（行程有起始日才生效）"},
                    "end_day": {"type": "integer", "description": "跨日卡片的結束日（含當天）；傳 0 可改回單日"},
                    "title": {"type": "string", "maxLength": 30, "description": "新的卡片名稱（簡短）"},
                    "place_name": {"type": "string", "description": "新的純地點名稱（含城市），用於地圖定位，不要放網址"},
                    "category": {"type": "string", "enum": ["景點", "美食", "交通", "住宿"], "description": "新的分類"},
                    "emoji": {"type": "string", "description": "新的 emoji"},
                    "start_time": {"type": "string", "description": "新的建議時間 HH:MM"},
                    "note": {"type": "string", "description": "新的卡片細節（markdown）"},
                    "booked": {"type": "boolean", "description": "是否已預定票券"},
                    "ticket_url": {"type": "string", "description": "票券／訂位連結（完整網址）；傳空字串可清除"},
                },
                "required": ["card_no"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_card",
            "description": "刪除一張既有卡片。card_no 用「目前卡片」清單的編號。",
            "parameters": {
                "type": "object",
                "properties": {
                    "card_no": {"type": "integer", "description": "要刪除的卡片編號（見「目前卡片」清單）"},
                },
                "required": ["card_no"],
            },
        },
    },
]


def _parse_time_str(v):
    from datetime import datetime as _dt
    if not v or not isinstance(v, str):
        return None
    try:
        return _dt.strptime(v, "%H:%M").time()
    except Exception:
        return None


def _maps_link_and_geocode_query(place_name: str | None) -> tuple[str | None, str | None]:
    """純地名 → Google Maps 連結（前端當可點地標用）＋ 原始地名（供 geocoding 取座標）。
    已是網址則直接沿用、不 geocode。回傳 (stored_place, geocode_query)。"""
    from urllib.parse import quote
    raw = (place_name or "").strip() or None
    if not raw:
        return None, None
    if raw.startswith("http"):
        return raw, None
    return f"https://www.google.com/maps/search/?api=1&query={quote(raw)}", raw


async def _ai_update_card(
    db: AsyncSession,
    user_id: UUID,
    trip_id: UUID,
    trip_start_date,
    item_id: UUID,
    args: dict,
) -> dict:
    from datetime import timedelta

    item = await crud_trips.get_item(db, trip_id, item_id)
    if item is None:
        return {"ok": False, "error": "card not found"}

    kwargs: dict = {}
    if args.get("title"):
        kwargs["title"] = str(args["title"]).strip()[:60]
    if "note" in args:
        kwargs["note"] = args.get("note") or None
    if "emoji" in args:
        kwargs["emoji"] = args.get("emoji") or None
    if "ticket_url" in args:
        kwargs["ticket_url"] = (args.get("ticket_url") or "").strip() or None
    if isinstance(args.get("booked"), bool):
        kwargs["booked"] = args["booked"]
    if "start_time" in args:
        kwargs["start_time"] = _parse_time_str(args.get("start_time"))
    if args.get("category"):
        kwargs["category"] = str(args["category"]).strip()

    # day → start_date（需 trip 有起始日）
    def _to_int(v):
        try:
            return int(v) if v not in (None, "") else None
        except (ValueError, TypeError):
            return None

    day_int = _to_int(args.get("day"))
    if trip_start_date and day_int and day_int >= 1:
        kwargs["start_date"] = trip_start_date + timedelta(days=day_int - 1)

    # end_day → end_date（跨日卡片）。傳 0／空可清除回單日
    if "end_day" in args:
        end_day_int = _to_int(args.get("end_day"))
        if trip_start_date and end_day_int and end_day_int >= 1:
            kwargs["end_date"] = trip_start_date + timedelta(days=end_day_int - 1)
        else:
            kwargs["end_date"] = None

    # place_name 變更 → 存成可點連結 + 背景 geocoding
    geocode_query = None
    if "place_name" in args:
        stored_place, geocode_query = _maps_link_and_geocode_query(args.get("place_name"))
        kwargs["place_name"] = stored_place
        if geocode_query:
            kwargs["geocoding_status"] = "pending"
            kwargs["lat"] = None
            kwargs["lng"] = None

    item = await crud_trips.update_item(db, item, **kwargs)

    # category → 對應 trip 標籤並掛到卡片（沿用 add_card 的行為，掛失敗不影響卡片）
    cat = (args.get("category") or "").strip()
    if cat in _CATEGORY_TAG_COLORS:
        try:
            from app.models.trip import TripItemTag as _TripItemTag
            from sqlalchemy import select
            tag = await crud_trips.get_or_create_tag(db, user_id, cat, _CATEGORY_TAG_COLORS[cat])
            exists = await db.execute(
                select(_TripItemTag).where(
                    _TripItemTag.trip_item_id == item.id,
                    _TripItemTag.trip_tag_id == tag.id,
                )
            )
            if exists.scalar_one_or_none() is None:
                db.add(_TripItemTag(trip_item_id=item.id, trip_tag_id=tag.id))
                await db.commit()
        except Exception:
            logger.exception("attach category tag failed for item %s", item.id)

    if geocode_query:
        asyncio.create_task(_geocode_items_bg([(item.id, geocode_query)]))

    return await _item_read_json(db, trip_id, item.id, ok=True, user_id=user_id)


async def _item_read_json(
    db: AsyncSession, trip_id: UUID, item_id: UUID, *, ok: bool, user_id: UUID | None = None
) -> dict:
    """把單張卡片組成給前端的工具結果：_item 放完整 TripItemRead（前端用來即時渲染卡片）。"""
    item = await crud_trips.get_item(db, trip_id, item_id)
    if item is None:
        return {"ok": False}
    source_map = (
        await _build_item_source_map(db, user_id, [item]) if user_id else None
    )
    read = _build_item_read(item, source_map)
    return {"ok": ok, "title": item.title, "_item": read.model_dump(mode="json")}


async def ai_edit_trip_stream(
    db: AsyncSession,
    user_id: UUID,
    trip_id: UUID,
    instruction: str,
    history: list[dict] | None = None,
):
    """AI 修改既有行程（SSE 串流）：依用戶指示用工具逐張新刪修卡片。

    每執行一個工具就 yield 一個 tool_result 事件，前端據此即時更新畫面：
      add_card / update_card → 帶完整卡片（_item）
      delete_card           → 帶 _deleted_id
    history 為先前的對話（[{role, content}]），讓多輪追問有記憶。
    行程不存在時 yield error 事件。
    """
    from app.services import ai_service

    trip = await crud_trips.get_trip(db, user_id, trip_id)
    if trip is None:
        yield ai_service._sse("error", {"message": "trip not found"})
        return

    # 以與詳情頁相同的排序呈現卡片，並建立 編號 → item_id 的對照
    items_sorted = sorted(
        trip.items or [],
        key=lambda i: (str(i.start_date) if i.start_date else "", i.order_index),
    )
    card_map: dict[int, UUID] = {}
    card_lines: list[str] = []
    for n, it in enumerate(items_sorted, start=1):
        card_map[n] = it.id
        meta = []
        if it.start_date:
            meta.append(str(it.start_date) + (f"~{it.end_date}" if it.end_date and it.end_date != it.start_date else ""))
        if it.start_time:
            meta.append(it.start_time.strftime("%H:%M"))
        if it.category:
            meta.append(it.category)
        meta_str = f"（{' · '.join(meta)}）" if meta else ""
        card_lines.append(f"{n}. {it.title}{meta_str}")

    header = [f"行程標題：{trip.title}"]
    if trip.start_date:
        header.append(f"起始日：{trip.start_date}")
    if trip.end_date:
        header.append(f"結束日：{trip.end_date}")
    cards_block = "\n".join(card_lines) if card_lines else "（目前沒有任何卡片）"
    user_message = (
        "\n".join(header)
        + "\n\n目前卡片：\n"
        + cards_block
        + "\n\n修改指示：\n"
        + instruction.strip()
    )

    trip_start_date = trip.start_date

    async def execute_tool(name: str, args: dict) -> dict:
        if name == "add_card":
            res = await add_card_from_chat(
                db, user_id, trip_id,
                day=args.get("day"),
                end_day=args.get("end_day"),
                title=args.get("title", "未命名"),
                place_name=args.get("place_name"),
                category=args.get("category"),
                emoji=args.get("emoji"),
                start_time=args.get("start_time"),
                note=args.get("note"),
                ticket_url=args.get("ticket_url"),
            )
            if not res or not res.get("id"):
                return {"ok": False}
            return await _item_read_json(db, trip_id, UUID(res["id"]), ok=True, user_id=user_id)

        if name == "update_card":
            try:
                no = int(args.get("card_no"))
            except (TypeError, ValueError):
                return {"ok": False, "error": "invalid card_no"}
            item_id = card_map.get(no)
            if item_id is None:
                return {"ok": False, "error": "card_no not found"}
            return await _ai_update_card(db, user_id, trip_id, trip_start_date, item_id, args)

        if name == "delete_card":
            try:
                no = int(args.get("card_no"))
            except (TypeError, ValueError):
                return {"ok": False, "error": "invalid card_no"}
            item_id = card_map.get(no)
            if item_id is None:
                return {"ok": False, "error": "card_no not found"}
            ok = await delete_item(db, user_id, trip_id, item_id)
            return {"ok": ok, "_deleted_id": str(item_id)}

        return {"ok": False, "error": "unknown tool"}

    from datetime import date as _date
    system = _TRIP_EDIT_SYSTEM + f"\n今天日期：{_date.today().isoformat()}"
    async for ev in ai_service.stream_tool_loop(
        system, user_message, _TRIP_EDIT_TOOLS, execute_tool, history=history
    ):
        yield ev

    # 標記為 AI 最後編輯（靜默，不另發事件）
    trip2 = await crud_trips.get_trip(db, user_id, trip_id)
    if trip2 is not None:
        await crud_trips.update_trip(db, trip2, last_edited_by="ai")
