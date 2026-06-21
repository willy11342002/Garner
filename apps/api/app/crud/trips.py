from uuid import UUID, uuid4

from sqlalchemy import exists, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.trip import Trip, TripItem, TripItemSource, TripItemTag, TripMember, TripTag
from app.models.user import User
from app.models.user_item import UserItem


# ── Trip ──────────────────────────────────────────────────────────────────────

async def create_trip(
    db: AsyncSession,
    user_id: UUID,
    *,
    title: str,
    summary: str | None = None,
    start_date=None,
    end_date=None,
    source_item_ids: list | None = None,
    last_edited_by: str = "user",
) -> Trip:
    trip = Trip(
        user_id=user_id,
        title=title,
        summary=summary,
        start_date=start_date,
        end_date=end_date,
        source_item_ids=[str(i) for i in (source_item_ids or [])],
        last_edited_by=last_edited_by,
    )
    db.add(trip)
    await db.commit()
    await db.refresh(trip)
    return trip


async def get_trip(db: AsyncSession, user_id: UUID, trip_id: UUID) -> Trip | None:
    """取得行程：owner 或成員皆可。"""
    result = await db.execute(
        select(Trip)
        .where(
            Trip.id == trip_id,
            or_(
                Trip.user_id == user_id,
                exists().where(
                    TripMember.trip_id == trip_id,
                    TripMember.member_user_id == user_id,
                ),
            ),
        )
        .options(
            selectinload(Trip.items).selectinload(TripItem.item_tags).selectinload(TripItemTag.trip_tag),
            selectinload(Trip.members),
        )
    )
    return result.scalar_one_or_none()


async def list_trips(db: AsyncSession, user_id: UUID) -> list[Trip]:
    """列出使用者擁有或已加入的所有行程。"""
    result = await db.execute(
        select(Trip)
        .where(
            or_(
                Trip.user_id == user_id,
                exists().where(
                    TripMember.trip_id == Trip.id,
                    TripMember.member_user_id == user_id,
                ),
            )
        )
        .options(selectinload(Trip.items), selectinload(Trip.members))
        .order_by(Trip.updated_at.desc())
    )
    return list(result.scalars().all())


async def update_trip(
    db: AsyncSession,
    trip: Trip,
    *,
    title: str | None = None,
    summary: str | None = None,
    start_date=None,
    end_date=None,
    last_edited_by: str | None = None,
) -> Trip:
    if title is not None:
        trip.title = title
    if summary is not None:
        trip.summary = summary
    if start_date is not None:
        trip.start_date = start_date
    if end_date is not None:
        trip.end_date = end_date
    if last_edited_by is not None:
        trip.last_edited_by = last_edited_by
    await db.commit()
    await db.refresh(trip)
    return trip


async def delete_trip(db: AsyncSession, trip: Trip) -> None:
    await db.delete(trip)
    await db.commit()


# ── TripItem ──────────────────────────────────────────────────────────────────

async def create_item(db: AsyncSession, trip_id: UUID, **kwargs) -> TripItem:
    item = TripItem(trip_id=trip_id, **kwargs)
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


async def get_item(
    db: AsyncSession, trip_id: UUID, item_id: UUID
) -> TripItem | None:
    result = await db.execute(
        select(TripItem)
        .where(TripItem.id == item_id, TripItem.trip_id == trip_id)
        .options(selectinload(TripItem.item_tags).selectinload(TripItemTag.trip_tag))
    )
    return result.scalar_one_or_none()


async def update_item(
    db: AsyncSession,
    item: TripItem,
    *,
    tag_ids: list[UUID] | None = None,
    **kwargs,
) -> TripItem:
    for k, v in kwargs.items():
        if v is not None or k in ("start_date", "end_date", "start_time", "end_time",
                                   "place_name", "lat", "lng", "note", "emoji", "ticket_url"):
            setattr(item, k, v)

    if tag_ids is not None:
        # 全替換 tags
        await db.execute(
            TripItemTag.__table__.delete().where(TripItemTag.trip_item_id == item.id)
        )
        for tid in tag_ids:
            db.add(TripItemTag(trip_item_id=item.id, trip_tag_id=tid))

    await db.commit()
    await db.refresh(item)
    return item


async def delete_item(db: AsyncSession, item: TripItem) -> None:
    await db.delete(item)
    await db.commit()


async def set_item_sources(
    db: AsyncSession, trip_item_id: UUID, user_item_ids: list[UUID]
) -> None:
    """全替換某張卡片的知識關聯（沿用 tag 的全替換寫法）。"""
    await db.execute(
        TripItemSource.__table__.delete().where(
            TripItemSource.trip_item_id == trip_item_id
        )
    )
    for uid in dict.fromkeys(user_item_ids):  # 去重、保序
        db.add(TripItemSource(trip_item_id=trip_item_id, user_item_id=uid))
    await db.commit()


async def reorder_items(
    db: AsyncSession,
    entries: list[dict],  # [{"id": UUID, "order_index": float}]
) -> None:
    for entry in entries:
        result = await db.execute(
            select(TripItem).where(TripItem.id == entry["id"])
        )
        item = result.scalar_one_or_none()
        if item:
            item.order_index = entry["order_index"]
    await db.commit()


# ── TripTag ───────────────────────────────────────────────────────────────────

async def list_tags(db: AsyncSession, user_id: UUID) -> list[TripTag]:
    result = await db.execute(
        select(TripTag)
        .where(TripTag.user_id == user_id)
        .order_by(TripTag.name)
    )
    return list(result.scalars().all())


async def get_or_create_tag(
    db: AsyncSession, user_id: UUID, name: str, color: str | None = None
) -> TripTag:
    result = await db.execute(
        select(TripTag).where(TripTag.user_id == user_id, TripTag.name == name)
    )
    tag = result.scalar_one_or_none()
    if tag:
        return tag
    tag = TripTag(user_id=user_id, name=name, color=color)
    db.add(tag)
    await db.commit()
    await db.refresh(tag)
    return tag


async def update_tag(
    db: AsyncSession, tag: TripTag, *, name: str | None = None, color: str | None = None
) -> TripTag:
    if name is not None:
        tag.name = name
    if color is not None:
        tag.color = color
    await db.commit()
    await db.refresh(tag)
    return tag


async def delete_tag(db: AsyncSession, tag: TripTag) -> None:
    await db.delete(tag)
    await db.commit()


async def get_tag(db: AsyncSession, user_id: UUID, tag_id: UUID) -> TripTag | None:
    result = await db.execute(
        select(TripTag).where(TripTag.id == tag_id, TripTag.user_id == user_id)
    )
    return result.scalar_one_or_none()


# ── TripMember ────────────────────────────────────────────────────────────────

async def get_trip_member(
    db: AsyncSession, trip_id: UUID, member_user_id: UUID
) -> TripMember | None:
    result = await db.execute(
        select(TripMember).where(
            TripMember.trip_id == trip_id,
            TripMember.member_user_id == member_user_id,
        )
    )
    return result.scalar_one_or_none()


async def get_trip_member_by_id(
    db: AsyncSession, trip_id: UUID, member_id: UUID
) -> TripMember | None:
    result = await db.execute(
        select(TripMember).where(
            TripMember.id == member_id,
            TripMember.trip_id == trip_id,
        )
    )
    return result.scalar_one_or_none()


async def list_trip_members(db: AsyncSession, trip_id: UUID) -> list[TripMember]:
    result = await db.execute(
        select(TripMember)
        .where(TripMember.trip_id == trip_id)
        .order_by(TripMember.created_at)
    )
    return list(result.scalars().all())


async def add_trip_member(
    db: AsyncSession,
    trip_id: UUID,
    member_user_id: UUID,
    role: str,
    invited_by: UUID,
) -> TripMember:
    member = TripMember(
        trip_id=trip_id,
        member_user_id=member_user_id,
        role=role,
        invited_by=invited_by,
    )
    db.add(member)
    await db.commit()
    await db.refresh(member)
    return member


async def update_trip_member_role(
    db: AsyncSession, member: TripMember, role: str
) -> TripMember:
    member.role = role
    await db.commit()
    await db.refresh(member)
    return member


async def remove_trip_member(db: AsyncSession, member: TripMember) -> None:
    await db.delete(member)
    await db.commit()


async def get_trip_by_invite_token(db: AsyncSession, token: UUID) -> Trip | None:
    result = await db.execute(
        select(Trip)
        .where(Trip.invite_token == token)
        .options(selectinload(Trip.members))
    )
    return result.scalar_one_or_none()


async def set_trip_invite_token(
    db: AsyncSession, trip: Trip, token: UUID | None, role: str
) -> Trip:
    trip.invite_token = token
    trip.invite_role = role
    await db.commit()
    await db.refresh(trip)
    return trip


# ── User lookup ───────────────────────────────────────────────────────────────

async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(
        select(User).where(User.email == email)
    )
    return result.scalar_one_or_none()


# ── Provenance ────────────────────────────────────────────────────────────────

async def resolve_sources(
    db: AsyncSession, user_id: UUID, source_item_ids: list
) -> list[UserItem]:
    if not source_item_ids:
        return []
    ids: list[UUID] = []
    for i in source_item_ids:
        try:
            ids.append(UUID(i) if isinstance(i, str) else i)
        except (ValueError, TypeError):
            continue
    if not ids:
        return []
    result = await db.execute(
        select(UserItem).where(UserItem.user_id == user_id, UserItem.id.in_(ids))
    )
    return list(result.scalars().all())
