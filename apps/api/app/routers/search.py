from uuid import UUID

from fastapi import APIRouter, Query

from app.dependencies import CurrentUser, DbSession
from app.quota_depends import SearchAccess
from app.schemas.item import ItemRead, PaginatedResult
from app.services import search_service

router = APIRouter()


@router.get("/", response_model=list[ItemRead])
async def keyword_search(q: str, current_user: CurrentUser, db: DbSession):
    return await search_service.text_search(db, UUID(current_user["sub"]), q)


@router.get("/semantic", response_model=PaginatedResult[ItemRead])
async def semantic_search(
    q: str,
    current_user: CurrentUser,
    db: DbSession,
    _access: SearchAccess,
    page: int = Query(default=1, ge=1),
):
    return await search_service.semantic_search(db, UUID(current_user["sub"]), q, page)
