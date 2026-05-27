from fastapi import APIRouter

from app.dependencies import CurrentUser, DbSession
from app.crud import users as crud_users
from app.schemas.user import UserRead

router = APIRouter()


@router.get("/me", response_model=UserRead)
async def me(current_user: CurrentUser, db: DbSession):
    user_id = current_user["sub"]
    user = await crud_users.get_by_id(db, user_id)
    if user is None:
        from uuid import UUID
        email = current_user.get("email")
        username = email.split("@")[0] if email else user_id
        user = await crud_users.get_or_create(db, UUID(user_id), email, username)
        await db.commit()
    return user
