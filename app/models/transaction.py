import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import enum

from app.database import Base


class TransactionStatus(str, enum.Enum):
    PENDING = "pending"
    AUTHORIZED = "authorized"
    FAILED = "failed"
    REFUNDED = "refunded"


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    payment_link_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("payment_links.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    buy_order: Mapped[str] = mapped_column(String(26), unique=True, nullable=False, index=True)
    session_id: Mapped[str] = mapped_column(String(61), nullable=False)
    token: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[TransactionStatus] = mapped_column(
        SQLEnum(TransactionStatus), default=TransactionStatus.PENDING, index=True
    )
    response_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    authorization_code: Mapped[str | None] = mapped_column(String(6), nullable=True)
    payment_type_code: Mapped[str | None] = mapped_column(String(3), nullable=True)
    installments_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    card_last_four: Mapped[str | None] = mapped_column(String(4), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )
    authorized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    webpay_response: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    payment_link: Mapped["PaymentLink"] = relationship("PaymentLink", back_populates="transactions")
