from uuid import UUID

from fastapi import APIRouter

from app.dependencies import CurrentUser, DbSession
from app.schemas.item import ItemRead
from app.services import search_service

router = APIRouter()


@router.get("/", response_model=list[ItemRead])
async def search(q: str, current_user: CurrentUser, db: DbSession):
    return await search_service.search(db, UUID(current_user["sub"]), q)
