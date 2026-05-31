from uuid import UUID

from pydantic import BaseModel, EmailStr


class UserRead(BaseModel):
    id: UUID
    email: EmailStr | None = None
    username: str
    avatar_url: str | None = None

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    username: str | None = None
    avatar_url: str | None = None
