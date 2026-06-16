import asyncio
from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.routers import admin, articles, auth, billing, chat, items, locations, notifications, pat, quota, reports, search, tags, trips, trip_tags

import logging
import sys
# DEBUG=true（本地開發）→ 全域 log 層級設為 DEBUG，看得到 AI chat 的逐步動作
_log_level = logging.DEBUG if settings.debug else logging.INFO
logging.basicConfig(
    level=_log_level,
    stream=sys.stdout,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
# 第三方在 DEBUG 下會洗版，壓回 INFO/WARNING，保留我們自己的 DEBUG log 清爽
for _name in ("httpx", "httpcore", "hpack", "asyncio"):
    logging.getLogger(_name).propagate = True
    logging.getLogger(_name).setLevel(logging.WARNING if settings.debug else logging.INFO)

if settings.sentry_dsn:
    sentry_sdk.init(dsn=settings.sentry_dsn, traces_sample_rate=0.2)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from sqlalchemy import text
    from app.core.database import engine
    from app.services.ai_service import load_model_configs
    from app.core.supabase import get_supabase

    await load_model_configs()

    # Pre-warm the DB connection pool so the first real request
    # doesn't pay the TCP+SSL handshake cost (~300ms).
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))

    try:
        supabase = await get_supabase()
        await supabase.storage.create_bucket("avatars", options={"public": True})
    except Exception:
        pass  # bucket 已存在

    async def _daily_maintenance():
        from app.workers.maintenance import run_maintenance
        while True:
            await asyncio.sleep(86400)  # 24 小時
            try:
                await run_maintenance()
            except Exception as e:
                import logging
                logging.getLogger(__name__).error("daily maintenance failed: %s", e)

    task = asyncio.create_task(_daily_maintenance())

    # 向 Gumroad 註冊 webhook（有設定 access token 才執行）
    if settings.gumroad_access_token and settings.gumroad_webhook_url:
        from app.services.gumroad_service import register_webhooks
        try:
            await register_webhooks(settings.gumroad_webhook_url)
        except Exception as e:
            logging.getLogger(__name__).warning("Gumroad webhook registration failed: %s", e)

    yield
    task.cancel()


app = FastAPI(title="Garner API", version="0.1.0", lifespan=lifespan)

_origins = [o.strip() for o in settings.allowed_origins.split(",")]
_origin_regex = r"chrome-extension://.*"

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_origin_regex=_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(admin.router, prefix="/admin", tags=["admin"])
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(pat.router, prefix="/auth/pat", tags=["pat"])
app.include_router(articles.router, prefix="/articles", tags=["articles"])
app.include_router(items.router, prefix="/items", tags=["items"])
app.include_router(locations.router, tags=["locations"])
app.include_router(tags.router, prefix="/tags", tags=["tags"])
app.include_router(search.router, prefix="/search", tags=["search"])
app.include_router(chat.router, prefix="/chat", tags=["chat"])
app.include_router(reports.router, prefix="/reports", tags=["reports"])
app.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
app.include_router(quota.router, prefix="/quota", tags=["quota"])
app.include_router(billing.router, prefix="/billing", tags=["billing"])
app.include_router(trips.router, prefix="/trips", tags=["trips"])
app.include_router(trip_tags.router, prefix="/trip-tags", tags=["trip-tags"])


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/health")
async def health():
    return {"status": "ok"}
