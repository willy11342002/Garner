from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.place_cache import PlaceCache


async def get(db: AsyncSession, place_id: str) -> PlaceCache | None:
    result = await db.execute(select(PlaceCache).where(PlaceCache.place_id == place_id))
    return result.scalar_one_or_none()


async def upsert(db: AsyncSession, place_id: str, data: dict) -> PlaceCache:
    existing = await get(db, place_id)
    now = datetime.now(timezone.utc)
    if existing is not None:
        for key, value in data.items():
            setattr(existing, key, value)
        existing.cached_at = now
    else:
        existing = PlaceCache(place_id=place_id, cached_at=now, **data)
        db.add(existing)
    await db.commit()
    await db.refresh(existing)
    return existing
