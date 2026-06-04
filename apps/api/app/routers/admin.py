from fastapi import APIRouter, Depends, Header, HTTPException, UploadFile, File
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.app_setting import AppSetting

router = APIRouter()


def _require_admin(x_admin_secret: str = Header(...)):
    if not settings.admin_secret or x_admin_secret != settings.admin_secret:
        raise HTTPException(status_code=403, detail="Forbidden")


@router.post("/youtube-cookies", dependencies=[Depends(_require_admin)])
async def upload_youtube_cookies(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    content = await file.read()
    cookies_text = content.decode("utf-8")

    result = await db.execute(select(AppSetting).where(AppSetting.key == "youtube_cookies"))
    setting = result.scalar_one_or_none()

    if setting:
        setting.value = cookies_text
    else:
        db.add(AppSetting(key="youtube_cookies", value=cookies_text, description="YouTube cookies for yt-dlp"))

    await db.commit()
    return {"status": "ok", "bytes": len(cookies_text)}


@router.get("/youtube-cookies/status", dependencies=[Depends(_require_admin)])
async def get_youtube_cookies_status(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AppSetting).where(AppSetting.key == "youtube_cookies"))
    setting = result.scalar_one_or_none()
    if not setting or not setting.value.strip():
        return {"set": False}
    return {"set": True, "updated_at": setting.updated_at, "bytes": len(setting.value)}


@router.delete("/youtube-cookies", dependencies=[Depends(_require_admin)])
async def delete_youtube_cookies(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AppSetting).where(AppSetting.key == "youtube_cookies"))
    setting = result.scalar_one_or_none()
    if setting:
        await db.delete(setting)
        await db.commit()
    return {"status": "ok"}
