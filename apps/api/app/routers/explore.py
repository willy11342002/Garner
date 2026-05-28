from uuid import UUID

from fastapi import APIRouter

from app.dependencies import CurrentUser, DbSession
from app.schemas.explore import ExploreStats
from app.services import explore_service

router = APIRouter()


@router.get("/stats", response_model=ExploreStats)
async def get_stats(current_user: CurrentUser, db: DbSession):
    return await explore_service.get_stats(db, UUID(current_user["sub"]))
