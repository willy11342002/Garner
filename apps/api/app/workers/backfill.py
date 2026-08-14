"""一次性 backfill 工作函式。

由 `routers/admin.py` 透過 BackgroundTasks 排入，router 端只負責驗證 admin secret
與排程，實際的批次邏輯（查詢 → 斷詞 → 寫回）放在這裡。
"""

import asyncio
import logging

from app.core.database import AsyncSessionLocal
from app.crud import items as crud_items
from app.services import ai_service

logger = logging.getLogger("garner.admin.backfill")


async def backfill_search_zh(batch_size: int = 50) -> None:
    """補齊既有 user_items 的 title_zh / notes_zh（hybrid search 上線後的一次性 backfill）。

    分批處理直到沒有待補的資料為止。單筆斷詞失敗時把 title_zh 標成空字串而非留 None，
    否則下一輪的 `WHERE title_zh IS NULL` 會無限重選同一筆。
    """
    async with AsyncSessionLocal() as db:
        total = 0
        while True:
            rows = await crud_items.get_missing_search_zh(db, batch_size)
            if not rows:
                break
            for ui in rows:
                try:
                    ui.title_zh, ui.notes_zh = await asyncio.gather(
                        ai_service.segment(ui.title or ""),
                        ai_service.segment(ui.notes_md or ""),
                    )
                except Exception:
                    logger.exception("backfill search_zh for item %s failed", ui.id)
                    ui.title_zh = ui.title_zh or ""
            await db.commit()
            total += len(rows)
        logger.info("backfill: segmented title_zh/notes_zh for %d user_items", total)
