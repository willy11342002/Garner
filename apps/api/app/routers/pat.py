import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.crud import personal_access_tokens as crud_pat
from app.dependencies import CurrentUser, DbSession

router = APIRouter()


class PATCreate(BaseModel):
    name: str


class PATRead(BaseModel):
    id: uuid.UUID
    name: str
    last_used_at: str | None
    created_at: str

    model_config = {"from_attributes": True}


class PATCreated(PATRead):
    token: str  # 只在建立時回傳一次


@router.post("", response_model=PATCreated, status_code=201)
async def create_pat(body: PATCreate, current_user: CurrentUser, db: DbSession):
    user_id = uuid.UUID(current_user["sub"])
    pat, raw_token = await crud_pat.create_pat(db, user_id, body.name)
    await db.commit()
    await db.refresh(pat)
    return PATCreated(
        id=pat.id,
        name=pat.name,
        last_used_at=pat.last_used_at.isoformat() if pat.last_used_at else None,
        created_at=pat.created_at.isoformat(),
        token=raw_token,
    )


@router.get("", response_model=list[PATRead])
async def list_pats(current_user: CurrentUser, db: DbSession):
    user_id = uuid.UUID(current_user["sub"])
    pats = await crud_pat.get_pats_by_user(db, user_id)
    return [
        PATRead(
            id=p.id,
            name=p.name,
            last_used_at=p.last_used_at.isoformat() if p.last_used_at else None,
            created_at=p.created_at.isoformat(),
        )
        for p in pats
    ]


@router.delete("/{pat_id}", status_code=204)
async def revoke_pat(pat_id: uuid.UUID, current_user: CurrentUser, db: DbSession):
    user_id = uuid.UUID(current_user["sub"])
    ok = await crud_pat.revoke_pat(db, pat_id, user_id)
    if not ok:
        raise HTTPException(status_code=404, detail="PAT not found")
    await db.commit()
