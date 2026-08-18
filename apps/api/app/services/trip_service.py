import asyncio
import logging
from uuid import UUID, uuid4

from google.genai import types
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import trips as crud_trips
from app.models.trip import Trip, TripItem, TripMember
from app.schemas.trip import (
    TripCreate,
    TripItemCreate,
    TripItemRead,
    TripItemReorderEntry,
    TripItemTagRead,
    TripItemUpdate,
    TripListItem,
    TripMemberRead,
    TripRead,
    TripSourceItem,
    TripUpdate,
)

# 卡片關聯知識的對照表型別：user_item_id → 已解析的來源資訊
SourceMap = dict[UUID, TripSourceItem]

logger = logging.getLogger(__name__)

# ── 角色權限 helper ────────────────────────────────────────────────────────────

_ROLE_RANK = {"viewer": 0, "editor": 1, "owner": 2}


def _get_effective_role(trip: Trip, user_id: UUID) -> str | None:
    if trip.user_id == user_id:
        return "owner"
    for m in trip.members:
        if m.member_user_id == user_id:
            return m.role
    return None


async def _get_accessible_trip(
    db: AsyncSession,
    user_id: UUID,
    trip_id: UUID,
    required_role: str = "viewer",
) -> tuple[Trip, str] | None:
    """取得行程並驗證最低角色需求。回傳 (trip, effective_role) 或 None（無權限 → 呼叫端回 404）。"""
    trip = await crud_trips.get_trip(db, user_id, trip_id)
    if trip is None:
        return None
    role = _get_effective_role(trip, user_id)
    if role is None or _ROLE_RANK.get(role, -1) < _ROLE_RANK.get(required_role, 0):
        return None
    return trip, role


async def _get_member_reads(db: AsyncSession, members: list[TripMember]) -> list[TripMemberRead]:
    """批次查詢成員的 email / username，組成 TripMemberRead 列表。"""
    if not members:
        return []
    from sqlalchemy import select
    from app.models.user import User
    ids = [m.member_user_id for m in members]
    result = await db.execute(select(User).where(User.id.in_(ids)))
    user_map = {u.id: u for u in result.scalars().all()}
    return [
        TripMemberRead(
            id=m.id,
            member_user_id=m.member_user_id,
            email=user_map[m.member_user_id].email or "" if m.member_user_id in user_map else "",
            display_name=user_map[m.member_user_id].username if m.member_user_id in user_map else None,
            role=m.role,
            created_at=m.created_at,
        )
        for m in members
    ]


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


async def _build_trip_read(
    db: AsyncSession, user_id: UUID, trip: Trip, my_role: str | None = None
) -> TripRead:
    if my_role is None:
        my_role = _get_effective_role(trip, user_id) or "owner"
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
    members = await _get_member_reads(db, trip.members or [])
    return TripRead(
        id=trip.id,
        title=trip.title,
        summary=trip.summary,
        start_date=trip.start_date,
        end_date=trip.end_date,
        last_edited_by=trip.last_edited_by,
        sources=sources,
        items=[_build_item_read(i, source_map) for i in items],
        my_role=my_role,
        members=members,
        invite_token=trip.invite_token if my_role == "owner" else None,
        invite_role=trip.invite_role,
        created_at=trip.created_at,
        updated_at=trip.updated_at,
    )


async def list_trips(db: AsyncSession, user_id: UUID) -> list[TripListItem]:
    rows = await crud_trips.list_trips(db, user_id)
    return [
        TripListItem(
            id=t.id,
            title=t.title,
            summary=t.summary,
            start_date=t.start_date,
            end_date=t.end_date,
            source_count=len(t.source_item_ids or []),
            item_count=item_count,   # SQL 算的，不是把卡片撈回來 len()
            member_count=len(t.members or []),
            my_role=_get_effective_role(t, user_id) or "owner",
            last_edited_by=t.last_edited_by,
            created_at=t.created_at,
            updated_at=t.updated_at,
        )
        for t, item_count in rows
    ]


async def get_trip(db: AsyncSession, user_id: UUID, trip_id: UUID) -> TripRead | None:
    trip = await crud_trips.get_trip(db, user_id, trip_id)
    if trip is None:
        return None
    my_role = _get_effective_role(trip, user_id) or "owner"
    return await _build_trip_read(db, user_id, trip, my_role=my_role)


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
    return await _build_trip_read(db, user_id, trip, my_role="owner")


async def create_trip_from_chat(
    db: AsyncSession,
    user_id: UUID,
    *,
    title: str,
    summary: str | None = None,
    start_date=None,
    end_date=None,
    source_item_ids: list | None = None,
) -> dict:
    """D 窗口的 create_trip：只建立「空」行程（標題＋日期區間），卡片交給 add_card 逐張加。

    這裡原本還收一個 cards=[...] 一次寫入所有卡片，但自從流程改成
    create_trip → add_card ×N 之後就沒有呼叫端了。它是第三份卡片欄位解析
    （自己一套 _parse_time／day 換算，欄位還比 add_card 少），留著只會再度分岔。
    """
    trip = await crud_trips.create_trip(
        db, user_id,
        title=title, summary=summary,
        start_date=_parse_date_str(start_date), end_date=_parse_date_str(end_date),
        source_item_ids=source_item_ids,
        last_edited_by="ai",
    )

    asyncio.create_task(_embed_trip_bg(trip.id, user_id))

    return {
        "id": str(trip.id),
        "title": trip.title,
        "summary": trip.summary,
        "item_count": 0,  # 剛建立時一定是空的，卡片由後續 add_card 加
    }


async def add_card_from_chat(
    db: AsyncSession, user_id: UUID, trip_id: UUID, args: dict
) -> dict:
    """D 窗口的 add_card：新增一張卡片，欄位與 update_card 完全一致。

    args 的解析走 `_card_args_to_kwargs`（與 `_ai_update_card` 同一條路徑）—— 能新增的
    欄位就一定能改回去，是靠共用那個函式保證的，不是靠兩邊各自記得加。
    """
    # 用 editor 權限（不是單純 get_trip）—— get_trip 對任何成員都放行，
    # viewer 不該能透過 AI 新增卡片，行為要跟 delete_item 一致
    accessible = await _get_accessible_trip(db, user_id, trip_id, required_role="editor")
    if accessible is None:
        return {"ok": False, "error": "trip not found"}
    trip = accessible[0]

    kwargs, extras = _card_args_to_kwargs(args)
    _mirror_card_dates(kwargs)

    # 建立時的必要預設值（update 沒給就是不動，create 沒給就得有個底）
    kwargs.setdefault("kind", "event")
    kwargs.setdefault("title", "未命名")
    kwargs.setdefault("booked", False)
    kwargs.setdefault("order_index", float(len(trip.items or [])))  # 接在現有卡片之後

    item = await crud_trips.create_item(db, trip_id, **kwargs)
    await _apply_card_extras(db, user_id, item, extras)

    asyncio.create_task(_embed_trip_bg(trip_id, user_id))
    result = {"ok": True, "id": str(item.id), "title": item.title}
    if extras.get("warnings"):
        result["warning"] = "; ".join(extras["warnings"])
    return result


async def _apply_card_extras(
    db: AsyncSession, user_id: UUID, item, extras: dict
) -> None:
    """卡片本體寫完之後的關聯欄位：標籤、知識關聯、背景 geocoding。

    這幾件事各自獨立 try —— 卡片已經寫進去了，掛標籤失敗不該讓整張卡視為失敗。
    add_card 與 update_card 共用。
    """
    from app.models.trip import TripItemTag as _TripItemTag
    from sqlalchemy import select

    async def _attach(name: str, color: str | None) -> None:
        tag = await crud_trips.get_or_create_tag(db, user_id, name, color)
        exists = await db.execute(
            select(_TripItemTag).where(
                _TripItemTag.trip_item_id == item.id,
                _TripItemTag.trip_tag_id == tag.id,
            )
        )
        if exists.scalar_one_or_none() is None:
            db.add(_TripItemTag(trip_item_id=item.id, trip_tag_id=tag.id))
            await db.commit()

    # tags 是全替換（模型傳 [] 就是清空），所以要先清再掛，且必須在 category 之前，
    # 否則 category 自動掛上的標籤會被 tags 的全替換洗掉。
    tag_names = extras.get("tag_names")
    if tag_names is not None:
        try:
            await db.execute(
                _TripItemTag.__table__.delete().where(_TripItemTag.trip_item_id == item.id)
            )
            await db.commit()
            for name in tag_names:
                await _attach(name, _CATEGORY_TAG_COLORS.get(name))
        except Exception:
            logger.exception("replace tags failed for item %s", item.id)

    # category（景點／美食／交通／住宿）對應成 trip 標籤並掛到卡片，
    # 否則 board 視圖會全擠在「無標籤」。
    cat = (extras.get("category") or "").strip()
    if cat in _CATEGORY_TAG_COLORS:
        try:
            await _attach(cat, _CATEGORY_TAG_COLORS[cat])
        except Exception:
            logger.exception("attach category tag failed for item %s", item.id)

    # 知識關聯（依地點對應的知識 item）。全替換，傳 [] 即清空。
    source_ids = extras.get("source_ids")
    if source_ids is not None:
        try:
            await crud_trips.set_item_sources(db, item.id, _parse_uuid_list(source_ids))
        except Exception:
            logger.exception("attach sources failed for item %s", item.id)

    if extras.get("geocode_query"):
        asyncio.create_task(_geocode_items_bg([(item.id, extras["geocode_query"])]))


def _parse_uuid_list(values: list[str] | None) -> list[UUID]:
    """把字串 id 清單轉成 UUID，解析失敗者略過。"""
    out: list[UUID] = []
    for v in values or []:
        try:
            out.append(v if isinstance(v, UUID) else UUID(str(v)))
        except (ValueError, TypeError):
            continue
    return out


async def _embed_trip_bg(trip_id: UUID, user_id: UUID) -> None:
    """背景更新 trip embedding，使用獨立 session。"""
    from app.core.database import AsyncSessionLocal
    from app.services import ai_service
    try:
        async with AsyncSessionLocal() as db:
            trip = await crud_trips.get_trip(db, user_id, trip_id)
            if trip is None:
                return
            parts = [trip.title]
            if trip.summary:
                parts.append(trip.summary)
            card_titles = [it.title for it in (trip.items or []) if it.title]
            if card_titles:
                parts.append(" ".join(card_titles))
            text = " ".join(parts)
            embedding = await ai_service.embed(text)
            await crud_trips.update_trip_embedding(db, trip, embedding)
    except Exception:
        logger.exception("trip embed failed for %s", trip_id)


async def search_trips_from_chat(
    db: AsyncSession,
    user_id: UUID,
    query: str | None,
    limit: int = 5,
) -> list[dict]:
    """chat 的 search_trips 工具用：有 query 時語意搜尋，否則列最近幾筆。"""
    from app.services import ai_service
    if query:
        embedding = await ai_service.embed(query)
        rows = await crud_trips.semantic_search_trips(db, user_id, embedding, limit=limit)
        if not rows:
            rows = await crud_trips.list_trips(db, user_id)
            rows = rows[:limit]
    else:
        rows = await crud_trips.list_trips(db, user_id)
        rows = rows[:limit]
    return [
        {
            "id": str(t.id),
            "title": t.title,
            "summary": t.summary,
            "item_count": item_count,
            "updated_at": t.updated_at.isoformat(),
        }
        for t, item_count in rows
    ]


async def get_trip_detail_for_chat(
    db: AsyncSession, user_id: UUID, trip_id: UUID
) -> dict | None:
    """D 窗口的 get_trip：讀一份行程的完整卡片清單。

    模型要改卡片就得先知道有哪些卡、id 是什麼，所以這是「查 → 讀 → 改」的中間那步。
    任何一份自己有權限的行程都讀得到，不限於使用者當前開著的那份。
    無權限或不存在回 None。
    """
    accessible = await _get_accessible_trip(db, user_id, trip_id, required_role="viewer")
    if accessible is None:
        return None
    trip = accessible[0]

    # 與詳情頁相同的排序，模型看到的順序就是使用者看到的順序
    items_sorted = sorted(
        trip.items or [],
        key=lambda i: (str(i.start_date) if i.start_date else "", i.order_index),
    )
    return {
        "id": str(trip.id),
        "title": trip.title,
        "start_date": str(trip.start_date) if trip.start_date else None,
        "end_date": str(trip.end_date) if trip.end_date else None,
        "cards": [
            {
                "card_id": str(it.id),
                "title": it.title,
                "start_date": str(it.start_date) if it.start_date else None,
                "end_date": str(it.end_date) if it.end_date else None,
                "start_time": it.start_time.strftime("%H:%M") if it.start_time else None,
                "category": it.category,
                "place_name": it.place_name,
            }
            for it in items_sorted
        ],
    }


async def build_trip_scope(db: AsyncSession, user_id: UUID, trip_id: UUID) -> dict | None:
    """使用者當前開著的行程，組成給 A 的一句提示。

    **這不是權限機制** —— 它只讓「把這個行程改短一點」有所指。實際能改哪一份完全由
    工具的 trip_id 決定，權限由資料層擋（見 _ai_update_card / add_card_from_chat）。
    """
    detail = await get_trip_detail_for_chat(db, user_id, trip_id)
    if detail is None:
        return None
    cards = "\n".join(
        f"- {c['title']}（card_id={c['card_id']}）" for c in detail["cards"]
    ) or "（目前沒有任何卡片）"
    brief = f"行程「{detail['title']}」（trip_id={detail['id']}）\n目前卡片：\n{cards}"
    return {"kind": "trip", "id": str(trip_id), "brief": brief}


async def update_card_from_chat(
    db: AsyncSession,
    user_id: UUID,
    trip_id: UUID,
    item_id: UUID,
    args: dict,
) -> dict:
    """D 窗口的 update_card：改一張既有卡片，回傳含 _item 的結果供前端即時更新。"""
    return await _ai_update_card(db, user_id, trip_id, item_id, args)


async def delete_card_from_chat(
    db: AsyncSession, user_id: UUID, trip_id: UUID, item_id: UUID
) -> dict:
    """D 窗口的 delete_card：刪一張卡片，回傳 _deleted_id 供前端即時移除。"""
    ok = await delete_item(db, user_id, trip_id, item_id)
    return {"ok": ok, "_deleted_id": str(item_id)}


async def card_read_json(
    db: AsyncSession, user_id: UUID, trip_id: UUID, item_id: UUID
) -> dict:
    """把一張卡片序列化成 _item payload（前端即時更新用）。"""
    return await _item_read_json(db, trip_id, item_id, ok=True, user_id=user_id)


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
    result = await _get_accessible_trip(db, user_id, trip_id, required_role="editor")
    if result is None:
        return None
    trip, my_role = result
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
    return await _build_trip_read(db, user_id, trip, my_role=my_role)


async def delete_trip(db: AsyncSession, user_id: UUID, trip_id: UUID) -> bool:
    result = await _get_accessible_trip(db, user_id, trip_id, required_role="owner")
    if result is None:
        return False
    trip, _ = result
    await crud_trips.delete_trip(db, trip)
    return True


# ── TripItem ──────────────────────────────────────────────────────────────────

async def add_item(
    db: AsyncSession, user_id: UUID, trip_id: UUID, data: TripItemCreate
) -> TripItemRead | None:
    result = await _get_accessible_trip(db, user_id, trip_id, required_role="editor")
    if result is None:
        return None
    trip, _ = result

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

    _mirror_card_dates(kwargs)
    item = await crud_trips.create_item(db, trip_id, **kwargs)

    # 注意：這裡不要讀 data.tag_ids。TripItemCreate 沒有這個欄位（只有 TripItemUpdate 有），
    # 原本的 `if data.tag_ids:` 會直接 AttributeError → 每次新增卡片都回 500。
    # 而且 create_item 在那之前就已經 commit，所以卡片其實有建立，只是前端拿到 500
    # 而不把它加進畫面，要重新整理才看得到。從 trips 功能第一版就是壞的。
    #
    # 建立時帶標籤這條路沒有任何呼叫端在用（前端是先建卡片、再 PATCH tag_ids；
    # AI 的 add_card 走 add_card_from_chat 直接進 crud），所以直接移除而不是補欄位。

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
    if await _get_accessible_trip(db, user_id, trip_id, required_role="editor") is None:
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

    _mirror_card_dates(update_kwargs, item)
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
    if await _get_accessible_trip(db, user_id, trip_id, required_role="editor") is None:
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
    if await _get_accessible_trip(db, user_id, trip_id, required_role="editor") is None:
        return False
    await crud_trips.reorder_items(
        db, [{"id": e.id, "order_index": e.order_index} for e in entries]
    )
    return True


# ── AI 修改既有行程 ──────────────────────────────────────────────────────────────
#
# 行程頁的 AI 懸浮球沒有專屬端口也沒有專屬引擎 —— 它就是打 chat 的
# POST /chat/sessions/{id}/messages，body 多帶 scope={"kind":"trip","id":...}。
# 這裡只剩兩種東西：build_trip_scope（組當前狀態給 chat_service.resolve_scope 用）、
# 以及卡片實際寫入的 helper（由 D 窗口的 executor 呼叫）。


def _parse_time_str(v):
    from datetime import datetime as _dt
    if not v or not isinstance(v, str):
        return None
    try:
        return _dt.strptime(v.strip(), "%H:%M").time()
    except Exception:
        return None


def _parse_date_str(v):
    """YYYY-MM-DD → date。空字串／格式不對回 None（呼叫端把 None 當「清空」）。

    已經是 date 就原樣放行 —— create_trip_from_chat 的參數沒有型別約束，呼叫端
    給 date 物件時不該被當成解析失敗而清成 None。
    """
    from datetime import date as _date, datetime as _dt
    if isinstance(v, _date):
        return v
    if not v or not isinstance(v, str):
        return None
    try:
        return _dt.strptime(v.strip(), "%Y-%m-%d").date()
    except Exception:
        return None


def _provided(v) -> bool:
    """這個值是模型「真的有話要說」，還是宣告了參數卻沒東西填的佔位空值？

    Gemini 常把工具宣告過的參數整組帶出來，沒話說的就給 "" 或 []。曾經把那種空值
    當成「清空這個欄位」，結果模型每改一張卡片就順手把沒提到的欄位一起洗掉：
    日期被清成 null（只剩時間）、tags 被清空、category 空字串連自動標籤都不掛。
    要清空必須走 clear_fields 明講。

    False 與 0 是有意義的值，所以不能用真值判斷。
    """
    if v is None:
        return False
    if isinstance(v, (bool, int, float)):
        return True
    if isinstance(v, str):
        return bool(v.strip())
    if isinstance(v, (list, tuple, dict, set)):
        return len(v) > 0
    return True


# clear_fields 能點名清空的欄位。必須是 crud_trips.update_item 白名單的子集，
# 否則設成 None 會被那邊當「呼叫端沒給值」而略過。
_CLEARABLE_COLUMNS = (
    "start_date", "end_date", "start_time", "end_time",
    "place_name", "note", "emoji", "ticket_url", "category",
)
_CLEARABLE_RELATIONS = {"tags": "tag_names", "source_item_ids": "source_ids"}


def _mirror_card_dates(kwargs: dict, item: TripItem | None = None) -> None:
    """卡片的兩個日期要嘛都有、要嘛都沒有：只給其中一個就補成同一天（就地改 kwargs）。

    判斷的是**合併後**的結果，不是只看這次送進來的欄位 —— 住宿卡片本來 8/22–8/25，
    只改 start_date 不該連帶把 end_date 洗掉。

    agent 與人工兩條路徑都要過這裡（add_card_from_chat／_ai_update_card 與 REST 的
    add_item／update_item），不然同一份資料會因為入口不同而長得不一樣。

    要把卡片改回未排程就兩個日期一起清（clear_fields 收陣列）；只清一個會被這裡補回來，
    因為「有結束日期卻沒有起始日期」不是一個有意義的狀態。
    """
    def resulting(key):
        if key in kwargs:
            return kwargs[key]
        return getattr(item, key, None) if item is not None else None

    start, end = resulting("start_date"), resulting("end_date")
    if start and not end:
        kwargs["end_date"] = start
    elif end and not start:
        kwargs["start_date"] = end


def _card_args_to_kwargs(args: dict) -> tuple[dict, dict]:
    """D 窗口工具的 args → 卡片欄位 kwargs。add_card 與 update_card 的**唯一**解析路徑。

    以前 add 與 update 各自解析一份，結果兩邊能力不對稱（update 有 booked、add 有
    source_item_ids，兩邊都沒有 end_time／kind／tags），而且加欄位要記得改兩處。

    **只有「有值」的欄位會被寫入**（見 `_provided`）—— 空字串／空陣列一律視為模型沒有
    要動這個欄位，不是要清空它。清空只認 clear_fields。

    回傳 (kwargs, extras)：
    - kwargs：直接餵給 crud_trips.create_item / update_item
    - extras：需要額外 I/O 的欄位（tag_names／source_ids／geocode_query），由
      `_apply_card_extras` 在卡片寫完後處理；warnings 會回給模型看
    """
    kwargs: dict = {}
    extras: dict = {}
    warnings: list[str] = []

    def given(key: str) -> bool:
        return _provided(args.get(key))

    # ── 排程 ──────────────────────────────────────────────────────────────────
    # 解析失敗就跳過（不清空），但要讓模型知道 —— 靜默沒寫進去正是先前那個
    # 「agent 說改好了、畫面上什麼都沒變」的老問題。
    for key in ("start_date", "end_date"):
        if given(key):
            parsed = _parse_date_str(args.get(key))
            if parsed is None:
                warnings.append(f"{key}={args.get(key)!r} is not a valid YYYY-MM-DD date, ignored")
            else:
                kwargs[key] = parsed
    for key in ("start_time", "end_time"):
        if given(key):
            parsed = _parse_time_str(args.get(key))
            if parsed is None:
                warnings.append(f"{key}={args.get(key)!r} is not a valid HH:MM time, ignored")
            else:
                kwargs[key] = parsed

    if given("order_index"):
        try:
            kwargs["order_index"] = float(args["order_index"])
        except (ValueError, TypeError):
            warnings.append(f"order_index={args.get('order_index')!r} is not a number, ignored")

    # ── 內容 ──────────────────────────────────────────────────────────────────
    if given("title"):
        # 防呆：title 過長截斷，避免整段敘述塞進標題
        kwargs["title"] = str(args["title"]).strip()[:60]
    for key in ("note", "emoji", "ticket_url", "category"):
        if given(key):
            kwargs[key] = str(args[key]).strip()
    if isinstance(args.get("booked"), bool):
        kwargs["booked"] = args["booked"]
    if args.get("kind") in ("event", "reference"):
        kwargs["kind"] = args["kind"]

    # place_name 前端當「可點的地圖連結」用，所以純地名要轉成 Google Maps 連結；
    # geocoding 仍用原始地名取座標（地圖標點靠 lat/lng，不靠這個連結）。
    if given("place_name"):
        stored_place, geocode_query = _maps_link_and_geocode_query(args.get("place_name"))
        kwargs["place_name"] = stored_place
        extras["geocode_query"] = geocode_query
        if geocode_query:
            kwargs["geocoding_status"] = "pending"
            kwargs["lat"] = None
            kwargs["lng"] = None

    # ── 關聯（寫完卡片才處理）──────────────────────────────────────────────────
    if given("tags"):
        extras["tag_names"] = [
            str(n).strip() for n in args["tags"] if _provided(n)
        ]
    if given("source_item_ids"):
        extras["source_ids"] = list(args["source_item_ids"])

    # ── 明確清空（放最後：跟上面衝突時以「要清掉」為準）────────────────────────
    raw_clear = args.get("clear_fields")
    for name in raw_clear if isinstance(raw_clear, list) else []:
        key = str(name).strip()
        if key in _CLEARABLE_RELATIONS:
            extras[_CLEARABLE_RELATIONS[key]] = []
        elif key in _CLEARABLE_COLUMNS:
            kwargs[key] = None
            if key == "place_name":
                kwargs["lat"] = kwargs["lng"] = None
                kwargs["geocoding_status"] = "done"
                extras.pop("geocode_query", None)
        else:
            warnings.append(f"clear_fields: {key!r} is not a clearable field, ignored")

    # 自動掛標籤要用「解析後」的 category，不能讓 _apply_card_extras 自己去讀原始 args ——
    # 那樣 clear_fields 清掉 category 之後還是會掛上標籤。
    if "category" in kwargs:
        extras["category"] = kwargs["category"]

    if warnings:
        extras["warnings"] = warnings
    return kwargs, extras


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
    item_id: UUID,
    args: dict,
) -> dict:
    # 權限在這裡擋 —— 工具收得到模型給的任意 trip_id，不是別人的就查不到。
    # （這條檢查原本不在：舊版只有 FAB 會呼叫，端口已先驗過權限。現在 chat 也能改
    #  任一份行程，少了它就是 IDOR。）
    accessible = await _get_accessible_trip(db, user_id, trip_id, required_role="editor")
    if accessible is None:
        return {"ok": False, "error": "trip not found"}

    item = await crud_trips.get_item(db, trip_id, item_id)
    if item is None:
        return {"ok": False, "error": "card not found"}

    kwargs, extras = _card_args_to_kwargs(args)
    _mirror_card_dates(kwargs, item)

    item = await crud_trips.update_item(db, item, **kwargs)
    await _apply_card_extras(db, user_id, item, extras)

    result = await _item_read_json(db, trip_id, item.id, ok=True, user_id=user_id)
    # warning 不帶底線 → 會灌回模型脈絡，讓它知道哪個欄位沒吃進去
    if extras.get("warnings"):
        result["warning"] = "; ".join(extras["warnings"])
    return result


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


async def mark_ai_edited(db: AsyncSession, user_id: UUID, trip_id: UUID) -> None:
    """agent 動過這份行程之後的收尾：標記 last_edited_by 並重算 embedding。

    由 chat_service 在 scope 是 trip 的那一輪跑完後呼叫一次（不是每張卡片各跑一次）。
    """
    accessible = await _get_accessible_trip(db, user_id, trip_id, required_role="editor")
    if accessible is None:
        return
    await crud_trips.update_trip(db, accessible[0], last_edited_by="ai")
    asyncio.create_task(_embed_trip_bg(trip_id, user_id))


# ── Trip 成員管理 ──────────────────────────────────────────────────────────────

async def list_members(
    db: AsyncSession, requester_id: UUID, trip_id: UUID
) -> list[TripMemberRead] | None:
    if await _get_accessible_trip(db, requester_id, trip_id, required_role="viewer") is None:
        return None
    members = await crud_trips.list_trip_members(db, trip_id)
    return await _get_member_reads(db, members)


async def invite_member_by_email(
    db: AsyncSession,
    owner_id: UUID,
    trip_id: UUID,
    email: str,
    role: str,
) -> TripMemberRead | None:
    """回傳 TripMemberRead；None 表示無權限或用戶不存在（呼叫端依 detail 判斷）。"""
    result = await _get_accessible_trip(db, owner_id, trip_id, required_role="owner")
    if result is None:
        return None
    trip, _ = result

    from app.crud import notifications as crud_notifications
    from app.models.notification import NotificationType
    from app.models.user import User
    from sqlalchemy import select

    # 查被邀請者
    invitee = await crud_trips.get_user_by_email(db, email)
    if invitee is None:
        return None  # 呼叫端區分 404 "user not found"

    if invitee.id == owner_id:
        return None  # 不能邀請自己

    existing = await crud_trips.get_trip_member(db, trip_id, invitee.id)
    if existing:
        # 已是成員 → 更新角色
        member = await crud_trips.update_trip_member_role(db, existing, role)
    else:
        member = await crud_trips.add_trip_member(db, trip_id, invitee.id, role, owner_id)

    # 取邀請者資訊組通知標題
    owner_result = await db.execute(select(User).where(User.id == owner_id))
    owner_user = owner_result.scalar_one_or_none()
    inviter_name = (owner_user.username or owner_user.email or "某人") if owner_user else "某人"

    await crud_notifications.create(
        db,
        user_id=invitee.id,
        type=NotificationType.trip_invited,
        title=f"{inviter_name} 邀請你加入旅遊行程「{trip.title}」",
        trip_id=trip_id,
    )
    await db.commit()

    reads = await _get_member_reads(db, [member])
    return reads[0] if reads else None


async def remove_member(
    db: AsyncSession, requester_id: UUID, trip_id: UUID, member_id: UUID
) -> bool:
    """owner 可移除任何成員；成員自己可離開行程。"""
    accessible = await _get_accessible_trip(db, requester_id, trip_id, required_role="viewer")
    if accessible is None:
        return False
    _, my_role = accessible

    member = await crud_trips.get_trip_member_by_id(db, trip_id, member_id)
    if member is None:
        return False

    # 只有 owner 可移除別人；一般成員只能移除自己
    if my_role != "owner" and member.member_user_id != requester_id:
        return False

    await crud_trips.remove_trip_member(db, member)
    return True


async def update_member_role(
    db: AsyncSession, owner_id: UUID, trip_id: UUID, member_id: UUID, role: str
) -> TripMemberRead | None:
    result = await _get_accessible_trip(db, owner_id, trip_id, required_role="owner")
    if result is None:
        return None

    member = await crud_trips.get_trip_member_by_id(db, trip_id, member_id)
    if member is None:
        return None

    member = await crud_trips.update_trip_member_role(db, member, role)
    reads = await _get_member_reads(db, [member])
    return reads[0] if reads else None


async def generate_invite_link(
    db: AsyncSession, owner_id: UUID, trip_id: UUID, role: str
) -> TripRead | None:
    result = await _get_accessible_trip(db, owner_id, trip_id, required_role="owner")
    if result is None:
        return None
    trip, _ = result

    token = uuid4()
    trip = await crud_trips.set_trip_invite_token(db, trip, token, role)
    return await _build_trip_read(db, owner_id, trip, my_role="owner")


async def revoke_invite_link(db: AsyncSession, owner_id: UUID, trip_id: UUID) -> bool:
    result = await _get_accessible_trip(db, owner_id, trip_id, required_role="owner")
    if result is None:
        return False
    trip, _ = result
    await crud_trips.set_trip_invite_token(db, trip, None, "viewer")
    return True


async def join_by_invite_token(
    db: AsyncSession, user_id: UUID, token: UUID
) -> TripMemberRead | None:
    trip = await crud_trips.get_trip_by_invite_token(db, token)
    if trip is None:
        return None

    # 已是 owner → 直接回傳（冪等）
    if trip.user_id == user_id:
        return None

    existing = await crud_trips.get_trip_member(db, trip.id, user_id)
    if existing:
        reads = await _get_member_reads(db, [existing])
        return reads[0] if reads else None

    member = await crud_trips.add_trip_member(db, trip.id, user_id, trip.invite_role, trip.user_id)
    await db.commit()
    reads = await _get_member_reads(db, [member])
    return reads[0] if reads else None
