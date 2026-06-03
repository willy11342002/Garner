from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile, status

from app.dependencies import CurrentUser, DbSession
from app.schemas.item import ArticleUpdate, ItemCreate, ItemRead
from app.services import item_service

router = APIRouter()

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5 MB


@router.post("/", response_model=ItemRead, status_code=status.HTTP_201_CREATED)
async def create_article(current_user: CurrentUser, db: DbSession, background_tasks: BackgroundTasks):
    return await item_service.create_item(db, UUID(current_user["sub"]), ItemCreate(), background_tasks)


@router.get("/{item_id}", response_model=ItemRead)
async def get_article(item_id: UUID, current_user: CurrentUser, db: DbSession):
    return await item_service.get_item(db, UUID(current_user["sub"]), item_id)


@router.patch("/{item_id}", response_model=ItemRead)
async def update_article(item_id: UUID, data: ArticleUpdate, current_user: CurrentUser, db: DbSession):
    return await item_service.update_article(db, UUID(current_user["sub"]), item_id, data)


@router.post("/{item_id}/publish", response_model=ItemRead)
async def publish_article(
    item_id: UUID, background_tasks: BackgroundTasks, current_user: CurrentUser, db: DbSession
):
    return await item_service.publish_article(db, UUID(current_user["sub"]), item_id, background_tasks)


@router.post("/{item_id}/cover", response_model=ItemRead)
async def upload_cover(item_id: UUID, file: UploadFile, current_user: CurrentUser, db: DbSession):
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Only JPEG, PNG, WebP are allowed")
    image_bytes = await file.read()
    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=400, detail="Image exceeds 5 MB limit")
    return await item_service.upload_article_cover(
        db, UUID(current_user["sub"]), item_id, image_bytes, file.content_type
    )
