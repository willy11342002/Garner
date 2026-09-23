"""一次性 backfill 工作函式。

由 `routers/admin.py` 透過 BackgroundTasks 排入，router 端只負責驗證 admin secret
與排程，實際的批次邏輯（查詢 → 斷詞 → 寫回）放在這裡。
"""

import asyncio
import logging

from app.core.database import AsyncSessionLocal
from app.crud import items as crud_items
from app.services import ai_service, apify_service, thumbnail_service

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


async def backfill_thumbnails(batch_size: int = 50) -> None:
    """把還指向平台 CDN 的 thumbnail_url 換成 Supabase Storage 的永久網址。

    2026-07 起 `quick_meta` 會在 `POST /items/` 當下就把 oEmbed / og:image 的網址寫進
    thumbnail_url，而背景 pipeline 當年只在欄位空白時才覆寫，於是 Storage 裡明明有快取、
    DB 卻留著幾天就過期的簽名網址（IG/FB 的 scontent、TikTok 的 x-expires）。

    逐筆先去 Storage 找同 id 的檔案，找得到就改寫；找不到的（快取當時就失敗）再用現有
    網址補抓一次——舊網址多半已經過期，抓不到就原樣留著，讓前端走無圖 placeholder。
    """
    relinked = recached = unrecoverable = 0
    after_id = None

    async with AsyncSessionLocal() as db:
        while True:
            rows = await crud_items.get_external_thumbnails(
                db, batch_size, thumbnail_service.PUBLIC_PATH_MARKER, after_id
            )
            if not rows:
                break
            after_id = rows[-1].id

            for ui in rows:
                cached_url = await thumbnail_service.find_cached(str(ui.id))
                if cached_url:
                    ui.thumbnail_url = cached_url
                    relinked += 1
                    continue

                image_bytes = await apify_service.download_bytes(ui.thumbnail_url)
                if image_bytes:
                    try:
                        ui.thumbnail_url = await thumbnail_service.cache(str(ui.id), image_bytes)
                        recached += 1
                        continue
                    except Exception:
                        logger.exception("backfill thumbnail cache for item %s failed", ui.id)
                unrecoverable += 1

            await db.commit()

    logger.info(
        "backfill thumbnails: relinked=%d recached=%d unrecoverable=%d",
        relinked,
        recached,
        unrecoverable,
    )
