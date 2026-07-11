import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class BankCreate(BaseModel):
    name: str
    logo: str | None = None


class BankUpdate(BaseModel):
    name: str | None = None
    logo: str | None = None


class BankReorder(BaseModel):
    ids: list[uuid.UUID]


class BankResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    logo: str | None
    position: int
    created_at: datetime
    updated_at: datetime


class AccountCreate(BaseModel):
    bank_id: uuid.UUID
    name: str
    account_type: str = "vista"
    balance: float = 0
    card_number: str | None = None
    color: str = "#1a1d2e"
    interest_rate: float = 0
    is_uf_indexed: bool = False
    deposit_date: datetime | None = None
    maturity_date: datetime | None = None
    withdrawals_this_year: int = 0
    max_free_withdrawals: int = 3


class AccountUpdate(BaseModel):
    name: str | None = None
    account_type: str | None = None
    balance: float | None = None
    card_number: str | None = None
    color: str | None = None
    interest_rate: float | None = None
    is_uf_indexed: bool | None = None
    deposit_date: datetime | None = None
    maturity_date: datetime | None = None
    withdrawals_this_year: int | None = None
    max_free_withdrawals: int | None = None


class AccountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    bank_id: uuid.UUID
    name: str
    account_type: str
    balance: float
    card_number: str | None
    color: str | None
    interest_rate: float
    last_interest_date: datetime | None
    is_uf_indexed: bool
    deposit_date: datetime | None
    maturity_date: datetime | None
    withdrawals_this_year: int
    max_free_withdrawals: int
    created_at: datetime
    updated_at: datetime


class CreditCardCreate(BaseModel):
    bank_id: uuid.UUID
    name: str
    franchise: str = "visa"
    credit_limit: float = 0
    used_credit: float = 0
    closing_day: int = 1
    payment_day: int = 10
    card_number: str | None = None
    color: str = "#1a1d2e"


class CreditCardUpdate(BaseModel):
    name: str | None = None
    franchise: str | None = None
    credit_limit: float | None = None
    used_credit: float | None = None
    closing_day: int | None = None
    payment_day: int | None = None
    card_number: str | None = None
    color: str | None = None


class CreditCardResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    bank_id: uuid.UUID
    name: str
    franchise: str
    credit_limit: float
    used_credit: float
    closing_day: int
    payment_day: int
    card_number: str | None
    color: str | None
    created_at: datetime
    updated_at: datetime


class TransactionCreate(BaseModel):
    bank_id: uuid.UUID
    account_id: uuid.UUID | None = None
    credit_card_id: uuid.UUID | None = None
    type: str
    amount: float
    merchant: str | None = None
    category: str | None = None
    description: str | None = None


class TransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    bank_id: uuid.UUID
    account_id: uuid.UUID | None
    credit_card_id: uuid.UUID | None
    type: str
    amount: float
    merchant: str | None
    category: str | None
    description: str | None
    created_at: datetime


class BankDataResponse(BaseModel):
    accounts: list[AccountResponse]
    credit_cards: list[CreditCardResponse]
    transactions: list[TransactionResponse]
