from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, EmailStr


class UserRead(BaseModel):
    id: UUID
    email: EmailStr
    name: str
    picture_url: str | None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
