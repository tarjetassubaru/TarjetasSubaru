import uuid
from datetime import datetime
from sqlalchemy import Integer, String, DateTime, Date, ForeignKey, Numeric, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class Bank(Base):
    __tablename__ = "banks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    logo: Mapped[str] = mapped_column(Text, nullable=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), onupdate=func.now()
    )


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    bank_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("banks.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    account_type: Mapped[str] = mapped_column(String(50), nullable=False, default="vista")
    balance: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    card_number: Mapped[str] = mapped_column(String(4), nullable=True)
    color: Mapped[str] = mapped_column(String(7), nullable=True, default="#1a1d2e")
    interest_rate: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    last_interest_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_uf_indexed: Mapped[bool] = mapped_column(default=False)
    deposit_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    maturity_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    withdrawals_this_year: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_free_withdrawals: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), onupdate=func.now()
    )


class CreditCard(Base):
    __tablename__ = "credit_cards"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    bank_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("banks.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    franchise: Mapped[str] = mapped_column(String(50), nullable=False, default="visa")
    credit_limit: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    used_credit: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    closing_day: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    payment_day: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    card_number: Mapped[str] = mapped_column(String(4), nullable=True)
    color: Mapped[str] = mapped_column(String(7), nullable=True, default="#1a1d2e")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), onupdate=func.now()
    )


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    bank_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("banks.id", ondelete="CASCADE"), nullable=False
    )
    account_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True
    )
    credit_card_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("credit_cards.id", ondelete="SET NULL"), nullable=True
    )
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    merchant: Mapped[str] = mapped_column(String(255), nullable=True)
    category: Mapped[str] = mapped_column(String(100), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now()
    )
