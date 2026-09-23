from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, status

from app.core.config import settings
from app.workers.backfill import backfill_search_zh, backfill_thumbnails

router = APIRouter()


async def _require_admin(x_admin_secret: str = Header(default="")) -> None:
    if not settings.admin_secret or x_admin_secret != settings.admin_secret:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


@router.post("/backfill/search-index", dependencies=[Depends(_require_admin)])
async def backfill_search_index(background_tasks: BackgroundTasks):
    """補齊既有 user_items 的 title_zh / notes_zh（hybrid search 上線後的一次性 backfill）。"""
    background_tasks.add_task(backfill_search_zh)
    return {"status": "queued"}


@router.post("/backfill/thumbnails", dependencies=[Depends(_require_admin)])
async def backfill_thumbnail_urls(background_tasks: BackgroundTasks):
    """把還指向平台 CDN（會過期）的 thumbnail_url 換回 Storage 快取網址。"""
    background_tasks.add_task(backfill_thumbnails)
    return {"status": "queued"}
