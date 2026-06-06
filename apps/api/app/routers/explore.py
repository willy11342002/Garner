from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from app.dependencies import CurrentUser, DbSession
from app.quota_depends import ExploreQuota
from app.schemas.explore import (
    ChainFullAnalysis,
    ChainFullRequest,
    ChainHopAnalysis,
    ChainHopRequest,
    ChainItem,
    ExploreStats,
    FocusQuery,
    FocusResult,
    PublicCollectionRead,
    SurpriseResult,
)
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


@router.post("/focus", response_model=FocusResult)
async def focus_query(body: FocusQuery, current_user: CurrentUser, db: DbSession):
    if not body.query.strip():
        raise HTTPException(status_code=422, detail="query cannot be empty")
    try:
        return await explore_service.focus_query(db, UUID(current_user["sub"]), body.query.strip())
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/surprise", response_model=SurpriseResult)
async def get_surprise(current_user: CurrentUser, db: DbSession, _quota: ExploreQuota):
    return await explore_service.get_surprise(db, UUID(current_user["sub"]))


@router.get("/chain/start", response_model=list[ChainItem])
async def chain_start(
    current_user: CurrentUser,
    db: DbSession,
    type: str = Query(default="random", pattern="^(forgotten|recent|random)$"),
):
    return await explore_service.get_chain_start_items(db, UUID(current_user["sub"]), type)


@router.get("/chain/next", response_model=list[ChainItem])
async def chain_next(
    current_user: CurrentUser,
    db: DbSession,
    item_id: UUID = Query(),
    exclude: str = Query(default=""),
):
    exclude_ids = [UUID(x) for x in exclude.split(",") if x]
    return await explore_service.get_chain_candidates(
        db, UUID(current_user["sub"]), item_id, exclude_ids
    )


@router.post("/chain/hop", response_model=ChainHopAnalysis)
async def chain_hop(body: ChainHopRequest, current_user: CurrentUser, db: DbSession, _quota: ExploreQuota):
    try:
        return await explore_service.analyze_hop(
            db, UUID(current_user["sub"]), body.from_item_id, body.to_item_id
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.post("/chain/full", response_model=ChainFullAnalysis)
async def chain_full(body: ChainFullRequest, current_user: CurrentUser, db: DbSession, _quota: ExploreQuota):
    if len(body.item_ids) < 2:
        raise HTTPException(status_code=422, detail="需要至少 2 個 item")
    try:
        return await explore_service.analyze_full_chain(
            db, UUID(current_user["sub"]), body.item_ids
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
