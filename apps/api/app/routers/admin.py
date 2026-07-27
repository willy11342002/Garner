import asyncio

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, status

from app.core.config import settings

router = APIRouter()


async def _require_admin(x_admin_secret: str = Header(default="")) -> None:
    if not settings.admin_secret or x_admin_secret != settings.admin_secret:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


@router.post("/backfill/search-index", dependencies=[Depends(_require_admin)])
async def backfill_search_index(background_tasks: BackgroundTasks):
    """補齊既有 user_items 的 title_zh / notes_zh（hybrid search 上線後的一次性 backfill）。"""
    background_tasks.add_task(_run_backfill_search_zh)
    return {"status": "queued"}


async def _run_backfill_search_zh(batch_size: int = 50):
    import logging
    from app.core.database import AsyncSessionLocal
    from sqlalchemy import select
    from app.models.user_item import UserItem
    from app.services import ai_service

    log = logging.getLogger("garner.admin.backfill")

    async with AsyncSessionLocal() as db:
        total = 0
        while True:
            rows = (await db.execute(
                select(UserItem)
                .where(UserItem.title_zh.is_(None), UserItem.title.is_not(None))
                .limit(batch_size)
            )).scalars().all()
            if not rows:
                break
            for ui in rows:
                try:
                    ui.title_zh, ui.notes_zh = await asyncio.gather(
                        ai_service.segment(ui.title or ""), ai_service.segment(ui.notes_md or ""),
                    )
                except Exception:
                    log.exception("backfill search_zh for item %s failed", ui.id)
                    # 標成空字串（而非留 None）避免下一輪 WHERE title_zh IS NULL 無限重選同一筆
                    ui.title_zh = ui.title_zh or ""
            await db.commit()
            total += len(rows)
        log.info("backfill: segmented title_zh/notes_zh for %d user_items", total)
