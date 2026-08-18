import asyncio
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import decode_token

bearer = HTTPBearer()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer)],
) -> dict:
    token = credentials.credentials

    try:
        # decode_token 內部的 PyJWKClient 在 JWK Set 快取過期時（預設 300 秒）會發一次
        # **同步阻塞**的 HTTPS 去抓 jwks.json。直接在 async def 裡呼叫會卡住整個 event
        # loop —— 在 Fly 的單核機上等於全站暫停。丟到 thread 執行緒跑。
        payload = await asyncio.to_thread(decode_token, token, settings.supabase_url)
        return payload
    except Exception as e:
        print(f"[auth] JWT decode error: {e}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


DbSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[dict, Depends(get_current_user)]
