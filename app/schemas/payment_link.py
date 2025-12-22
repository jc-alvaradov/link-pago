from datetime import datetime, timezone
from uuid import UUID
from pydantic import BaseModel, Field, field_validator

from app.models.payment_link import PaymentLinkStatus

MAX_AMOUNT_CLP = 999_999_999  # ~1 billion CLP


class PaymentLinkCreate(BaseModel):
    amount: int = Field(..., ge=50, le=MAX_AMOUNT_CLP, description="Monto en CLP (mínimo 50)")
    description: str = Field(..., min_length=1, max_length=500)
    single_use: bool = True
    expires_at: datetime | None = None
    extra_data: dict = Field(default_factory=dict)

    @field_validator("expires_at")
    @classmethod
    def validate_expires_at(cls, v: datetime | None) -> datetime | None:
        if v is not None and v <= datetime.now(timezone.utc):
            raise ValueError("La fecha de expiración debe ser en el futuro")
        return v


class PaymentLinkUpdate(BaseModel):
    description: str | None = Field(None, min_length=1, max_length=500)
    expires_at: datetime | None = None
    status: PaymentLinkStatus | None = None

    @field_validator("expires_at")
    @classmethod
    def validate_expires_at(cls, v: datetime | None) -> datetime | None:
        if v is not None and v <= datetime.now(timezone.utc):
            raise ValueError("La fecha de expiración debe ser en el futuro")
        return v


class PaymentLinkRead(BaseModel):
    id: UUID
    slug: str
    amount: int
    description: str
    currency: str
    status: PaymentLinkStatus
    single_use: bool
    times_paid: int
    expires_at: datetime | None
    views_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
