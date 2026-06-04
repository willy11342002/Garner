from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.routers import admin, articles, auth, chat, collections, explore, items, notifications, search, share, tags

import logging
logging.basicConfig(level=logging.INFO)

if settings.sentry_dsn:
    sentry_sdk.init(dsn=settings.sentry_dsn, traces_sample_rate=0.2)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.services.ai_service import load_model_configs
    from app.services.thumbnail_service import _get_supabase
    await load_model_configs()
    try:
        supabase = await _get_supabase()
        await supabase.storage.create_bucket("avatars", options={"public": True})
    except Exception:
        pass  # bucket 已存在
    yield


app = FastAPI(title="Vela API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(admin.router, prefix="/admin", tags=["admin"])
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(articles.router, prefix="/articles", tags=["articles"])
app.include_router(items.router, prefix="/items", tags=["items"])
app.include_router(tags.router, prefix="/tags", tags=["tags"])
app.include_router(collections.router, prefix="/collections", tags=["collections"])
app.include_router(search.router, prefix="/search", tags=["search"])
app.include_router(explore.router, prefix="/explore", tags=["explore"])
app.include_router(share.router, prefix="/share", tags=["share"])
app.include_router(chat.router, prefix="/chat", tags=["chat"])
app.include_router(notifications.router, prefix="/notifications", tags=["notifications"])


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/health")
async def health():
    return {"status": "ok"}
