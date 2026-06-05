from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import decode_token
from app.crud import personal_access_tokens as crud_pat
from app.crud import users as crud_users

bearer = HTTPBearer()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    token = credentials.credentials

    # PAT 驗證
    if token.startswith("pat_"):
        user_id = await crud_pat.get_user_id_by_token(db, token)
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid PAT")
        await db.commit()

        # 回傳與 JWT payload 相容的格式，只需要 sub
        user = await crud_users.get_by_id(db, user_id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        return {"sub": str(user_id), "email": user.email}

    # JWT 驗證（原有邏輯）
    try:
        payload = decode_token(token, settings.supabase_url)
        return payload
    except Exception as e:
        print(f"[auth] JWT decode error: {e}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


DbSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[dict, Depends(get_current_user)]
