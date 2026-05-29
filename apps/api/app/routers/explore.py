from uuid import UUID

from fastapi import APIRouter, Query

from app.dependencies import CurrentUser, DbSession
from app.schemas.explore import ExploreStats, PublicCollectionRead
from app.services import explore_service

router = APIRouter()


@router.get("/stats", response_model=ExploreStats)
async def get_stats(current_user: CurrentUser, db: DbSession):
    return await explore_service.get_stats(db, UUID(current_user["sub"]))


@router.get("/browse", response_model=list[PublicCollectionRead])
async def browse_public_collections(
    current_user: CurrentUser,
    db: DbSession,
    q: str | None = Query(default=None),
    tag: str | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=24, ge=1, le=100),
):
    return await explore_service.browse_public_collections(db, q=q, tag=tag, offset=offset, limit=limit)
