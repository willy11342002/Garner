from supabase import AsyncClient, acreate_client

from app.core.config import settings

_supabase: AsyncClient | None = None


async def get_supabase() -> AsyncClient:
    global _supabase
    if _supabase is None:
        _supabase = await acreate_client(settings.supabase_url, settings.supabase_service_key)
    return _supabase
