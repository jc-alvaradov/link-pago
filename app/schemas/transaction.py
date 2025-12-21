from datetime import datetime
from uuid import UUID
from pydantic import BaseModel

from app.models.transaction import TransactionStatus


class TransactionRead(BaseModel):
    id: UUID
    payment_link_id: UUID
    buy_order: str
    status: TransactionStatus
    response_code: int | None
    authorization_code: str | None
    payment_type_code: str | None
    installments_number: int | None
    amount: int
    card_last_four: str | None
    card_type: str | None
    payer_email: str | None
    created_at: datetime
    authorized_at: datetime | None

    class Config:
        from_attributes = True
