from uuid import UUID

from pydantic import BaseModel, EmailStr


class UserRead(BaseModel):
    id: UUID
    email: EmailStr | None = None
    username: str
    avatar_url: str | None = None
    allow_public_chain: bool = True

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    allow_public_chain: bool | None = None
