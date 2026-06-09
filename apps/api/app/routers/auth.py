from fastapi import APIRouter, HTTPException

from app.dependencies import CurrentUser, DbSession
from app.crud import users as crud_users
from app.schemas.user import UserRead, UserUpdate

router = APIRouter()


def _pick_avatar(jwt_payload: dict) -> str | None:
    """
    Supabase 在多 provider 情況下的行為：
    - GitHub 登入只寫 user_metadata.avatar_url，不動 user_metadata.picture
    - Google 登入同時寫 avatar_url 和 picture

    所以依 app_metadata.provider（第一個註冊的 provider）來決定要用哪個欄位：
    - 第一個是 google → 用 picture（GitHub 登入不會覆蓋這欄）
    - 第一個是 github → 用 avatar_url（GitHub 的原生欄位）
    - 其他情況 → avatar_url 優先，picture 備用
    """
    user_metadata: dict = jwt_payload.get("user_metadata") or {}
    app_metadata: dict = jwt_payload.get("app_metadata") or {}
    primary_provider: str = app_metadata.get("provider", "")

    if primary_provider == "google":
        return user_metadata.get("picture") or user_metadata.get("avatar_url")
    elif primary_provider == "github":
        return user_metadata.get("avatar_url") or user_metadata.get("picture")
    else:
        return user_metadata.get("avatar_url") or user_metadata.get("picture")


@router.get("/me", response_model=UserRead)
async def me(current_user: CurrentUser, db: DbSession):
    from uuid import UUID
    user_id = current_user["sub"]
    avatar_url: str | None = _pick_avatar(current_user)
    user = await crud_users.get_by_id(db, user_id)
    if user is None:
        email = current_user.get("email")
        username = email.split("@")[0] if email else user_id
        user = await crud_users.get_or_create(db, UUID(user_id), email, username, avatar_url)
        await db.commit()
    elif avatar_url and user.avatar_url != avatar_url:
        # 每次登入都同步 OAuth 頭像
        user.avatar_url = avatar_url
        await db.commit()
    return user


@router.put("/me", response_model=UserRead)
async def update_me(body: UserUpdate, current_user: CurrentUser, db: DbSession):
    from uuid import UUID
    user_id = current_user["sub"]
    user = await crud_users.get_by_id(db, UUID(user_id))
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    await crud_users.update_user(db, user)
    await db.commit()
    await db.refresh(user)
    return user


@router.delete("/me", status_code=204)
async def delete_me(current_user: CurrentUser, db: DbSession):
    from uuid import UUID
    from app.core.supabase import get_supabase

    user_id = current_user["sub"]
    user = await crud_users.get_by_id(db, UUID(user_id))
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    await crud_users.delete_user(db, user)
    await db.commit()

    # 從 Supabase Auth 刪除用戶
    try:
        supabase = await get_supabase()
        await supabase.auth.admin.delete_user(user_id)
    except Exception:
        pass
