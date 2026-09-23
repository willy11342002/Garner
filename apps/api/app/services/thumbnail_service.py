"""thumbnail_service：縮圖在 Supabase Storage 的快取層。

路徑慣例集中在這裡（bucket 由 `settings.storage_bucket` 指定，檔案一律放
`thumbnails/{item_id}.{ext}`），providers、item_service、backfill 都走這支，
不要再各自拼路徑。

**為什麼一定要快取**：平台給的縮圖網址是短期簽名網址（IG/FB 的 scontent 帶 `oe=`、
TikTok 帶 `x-expires`／`x-signature`），少則幾小時多則幾天就失效，直接存進 DB 的話
收藏當下看得到、隔幾天回來整批破圖。只有這裡回傳的 Storage 公開網址是永久的。
"""
import logging

from app.core.config import settings
from app.core.supabase import get_supabase

logger = logging.getLogger(__name__)

# get_public_url 產出的路徑片段，用來判斷一條網址是不是自家 Storage。
PUBLIC_PATH_MARKER = "/storage/v1/object/public/"

# 上傳只會產生 jpg／png，查找既有檔案時兩種都試。
_EXTENSIONS = ("jpg", "png")


def _path(item_id: str, ext: str = "jpg") -> str:
    return f"thumbnails/{item_id}.{ext}"


def _ext_from_content_type(content_type: str) -> str:
    return "png" if "png" in content_type.lower() else "jpg"


def is_cached_url(url: str | None) -> bool:
    """網址是否指向自家 Storage（永久），而不是會過期的平台 CDN。"""
    return bool(url and PUBLIC_PATH_MARKER in url)


async def public_url(item_id: str, ext: str = "jpg") -> str:
    supabase = await get_supabase()
    return await supabase.storage.from_(settings.storage_bucket).get_public_url(_path(item_id, ext))


async def cache(item_id: str, image_bytes: bytes, content_type: str = "image/jpeg") -> str:
    """上傳縮圖並回傳公開網址。上傳失敗時拋出，由呼叫端決定要退路還是回錯誤。"""
    ext = _ext_from_content_type(content_type)
    supabase = await get_supabase()
    await supabase.storage.from_(settings.storage_bucket).upload(
        _path(item_id, ext), image_bytes, {"content-type": content_type, "upsert": "true"}
    )
    url = await public_url(item_id, ext)
    logger.info("Thumbnail cached: %s", url)
    return url


async def find_cached(item_id: str) -> str | None:
    """Storage 裡已經有這個 item 的縮圖就回傳公開網址，否則 None。"""
    supabase = await get_supabase()
    try:
        entries = await supabase.storage.from_(settings.storage_bucket).list(
            "thumbnails", {"search": f"{item_id}."}
        )
    except Exception:
        logger.warning("Thumbnail lookup failed for item_id=%s", item_id, exc_info=True)
        return None

    names = {entry.get("name") for entry in entries or []}
    for ext in _EXTENSIONS:
        if f"{item_id}.{ext}" in names:
            return await public_url(item_id, ext)
    return None


async def remove(item_id: str) -> None:
    """刪掉這個 item 的所有縮圖檔；不存在或刪不掉都不算錯。"""
    supabase = await get_supabase()
    for ext in _EXTENSIONS:
        try:
            await supabase.storage.from_(settings.storage_bucket).remove([_path(item_id, ext)])
        except Exception:
            logger.debug("Thumbnail remove skipped: item_id=%s ext=%s", item_id, ext, exc_info=True)
