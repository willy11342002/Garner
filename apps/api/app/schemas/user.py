from uuid import UUID

from pydantic import BaseModel, EmailStr


class UserRead(BaseModel):
    id: UUID
    email: EmailStr
    avatar_url: str | None = None

    model_config = {"from_attributes": True}
