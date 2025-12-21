from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, EmailStr


class UserBase(BaseModel):
    email: EmailStr
    name: str


class UserRead(UserBase):
    id: UUID
    picture_url: str | None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
