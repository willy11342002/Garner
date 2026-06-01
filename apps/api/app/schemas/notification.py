from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.models.notification import NotificationType


class NotificationRead(BaseModel):
    id: UUID
    type: NotificationType
    title: str
    body: str | None
    item_id: UUID | None
    is_read: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationMarkRead(BaseModel):
    ids: list[UUID]
