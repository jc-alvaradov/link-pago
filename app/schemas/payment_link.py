from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, field_validator

from app.models.payment_link import PaymentLinkStatus


class PaymentLinkBase(BaseModel):
    amount: int = Field(..., ge=50, description="Monto en CLP (mínimo 50)")
    description: str = Field(..., min_length=1, max_length=500)


class PaymentLinkCreate(PaymentLinkBase):
    single_use: bool = True
    expires_at: datetime | None = None
    extra_data: dict = Field(default_factory=dict)

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: int) -> int:
        if v < 50:
            raise ValueError("El monto mínimo es 50 CLP")
        return v


class PaymentLinkUpdate(BaseModel):
    description: str | None = Field(None, min_length=1, max_length=500)
    expires_at: datetime | None = None
    status: PaymentLinkStatus | None = None


class PaymentLinkRead(PaymentLinkBase):
    id: UUID
    slug: str
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
