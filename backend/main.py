import asyncio
import base64
import logging
import math
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import init_db, get_db, async_session
from models import Bank, Account, CreditCard, Transaction
from schemas import (
    BankCreate, BankUpdate, BankReorder, BankResponse, BankDataResponse,
    AccountCreate, AccountUpdate, AccountResponse,
    CreditCardCreate, CreditCardUpdate, CreditCardResponse,
    TransactionCreate, TransactionResponse,
    TransferCreate, TransferResponse,
)

logger = logging.getLogger("credito_subaru")
WEEKLY_INTEREST_INTERVAL = 7 * 24 * 60 * 60


async def apply_weekly_interest():
    while True:
        await asyncio.sleep(WEEKLY_INTEREST_INTERVAL)
        try:
            async with async_session() as session:
                result = await session.execute(
                    select(Account).where(Account.interest_rate > 0)
                )
                accounts = result.scalars().all()
                now = datetime.now(timezone.utc)
                for account in accounts:
                    last = account.last_interest_date
                    if last is None:
                        account.last_interest_date = now
                        continue
                    if last.tzinfo is None:
                        last = last.replace(tzinfo=timezone.utc)
                    days = (now - last).days
                    if days <= 0:
                        continue
                    annual_rate = float(account.interest_rate) / 100
                    daily_rate = math.pow(1 + annual_rate, 1 / 365) - 1
                    balance = float(account.balance)
                    new_balance = balance * math.pow(1 + daily_rate, days)
                    earned = round(new_balance - balance, 2)
                    if earned <= 0:
                        continue
                    account.balance = round(new_balance, 2)
                    account.last_interest_date = now
                    txn = Transaction(
                        bank_id=account.bank_id,
                        account_id=account.id,
                        type="ingreso",
                        amount=earned,
                        merchant="Intereses automaticos",
                        category="Intereses",
                        description=f"Interes semanal {account.interest_rate}% anual - {days} dias",
                    )
                    session.add(txn)
                await session.commit()
                logger.info(f"Applied weekly interest to {len(accounts)} accounts")
        except Exception as e:
            logger.error(f"Error applying weekly interest: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    task = asyncio.create_task(apply_weekly_interest())
    yield
    task.cancel()


app = FastAPI(title="Credito Subaru API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"status": "ok", "service": "Credito Subaru API"}


@app.get("/api/banks", response_model=list[BankResponse])
async def list_banks(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Bank).order_by(Bank.position))
    banks = result.scalars().all()
    return banks


ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".svg"}


MIME_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".svg": "image/svg+xml",
}


def save_logo(file: UploadFile) -> str | None:
    if not file.filename:
        return None
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Formato no soportado: {ext}")
    content = file.file.read()
    b64 = base64.b64encode(content).decode("utf-8")
    mime = MIME_TYPES.get(ext, "image/png")
    return f"data:{mime};base64,{b64}"


@app.post("/api/banks", response_model=BankResponse, status_code=status.HTTP_201_CREATED)
async def create_bank(
    name: str = Form(...),
    logo: UploadFile | None = File(None),
    db: AsyncSession = Depends(get_db),
):
    logo_path = save_logo(logo) if logo else None

    result = await db.execute(select(Bank).order_by(Bank.position.desc()))
    last_bank = result.scalars().first()
    next_position = (last_bank.position + 1) if last_bank else 1

    bank = Bank(name=name, logo=logo_path, position=next_position)
    db.add(bank)
    await db.commit()
    await db.refresh(bank)
    return bank


@app.put("/api/banks/reorder", response_model=list[BankResponse])
async def reorder_banks(data: BankReorder, db: AsyncSession = Depends(get_db)):
    banks = []
    for idx, bank_id in enumerate(data.ids):
        result = await db.execute(select(Bank).where(Bank.id == bank_id))
        bank = result.scalar_one_or_none()
        if bank:
            bank.position = idx + 1
            banks.append(bank)
    await db.commit()
    for bank in banks:
        await db.refresh(bank)
    banks.sort(key=lambda b: b.position)
    return banks


@app.put("/api/banks/{bank_id}", response_model=BankResponse)
async def update_bank(bank_id: uuid.UUID, data: BankUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Bank).where(Bank.id == bank_id))
    bank = result.scalar_one_or_none()
    if not bank:
        raise HTTPException(status_code=404, detail="Bank not found")
    if data.name is not None:
        bank.name = data.name
    if data.logo is not None:
        bank.logo = data.logo
    await db.commit()
    await db.refresh(bank)
    return bank


@app.delete("/api/banks/{bank_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bank(bank_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Bank).where(Bank.id == bank_id))
    bank = result.scalar_one_or_none()
    if not bank:
        raise HTTPException(status_code=404, detail="Bank not found")
    await db.delete(bank)
    await db.commit()


@app.get("/api/banks/{bank_id}/data", response_model=BankDataResponse)
async def get_bank_data(bank_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    accounts = (await db.execute(select(Account).where(Account.bank_id == bank_id).order_by(Account.created_at))).scalars().all()
    cards = (await db.execute(select(CreditCard).where(CreditCard.bank_id == bank_id).order_by(CreditCard.created_at))).scalars().all()
    txns = (await db.execute(select(Transaction).where(Transaction.bank_id == bank_id).order_by(Transaction.created_at.desc()).limit(20))).scalars().all()
    return BankDataResponse(accounts=accounts, credit_cards=cards, transactions=txns)


@app.get("/api/accounts", response_model=list[AccountResponse])
async def list_accounts(bank_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Account).where(Account.bank_id == bank_id).order_by(Account.created_at))
    return result.scalars().all()


@app.post("/api/accounts", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
async def create_account(data: AccountCreate, db: AsyncSession = Depends(get_db)):
    account_data = data.model_dump()
    if data.interest_rate > 0:
        account_data["last_interest_date"] = datetime.now(timezone.utc)
    account = Account(**account_data)
    db.add(account)
    await db.commit()
    await db.refresh(account)
    return account


@app.post("/api/accounts/{account_id}/apply-interest", response_model=AccountResponse)
async def apply_interest(account_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Account).where(Account.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    if account.interest_rate <= 0:
        return account

    now = datetime.now(timezone.utc)
    if account.last_interest_date is None:
        account.last_interest_date = now
        await db.commit()
        await db.refresh(account)
        return account

    last = account.last_interest_date
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    days = (now - last).days
    if days <= 0:
        return account

    annual_rate = float(account.interest_rate) / 100
    daily_rate = math.pow(1 + annual_rate, 1 / 365) - 1
    balance = float(account.balance)
    new_balance = balance * math.pow(1 + daily_rate, days)
    earned = new_balance - balance

    account.balance = round(new_balance, 2)
    account.last_interest_date = now

    transaction = Transaction(
        bank_id=account.bank_id,
        account_id=account.id,
        type="ingreso",
        amount=round(earned, 2),
        merchant="Intereses MP",
        category="Intereses",
        description=f"Interes compuesto {account.interest_rate}% anual - {days} dias",
    )
    db.add(transaction)
    await db.commit()
    await db.refresh(account)
    return account


@app.put("/api/accounts/{account_id}", response_model=AccountResponse)
async def update_account(account_id: uuid.UUID, data: AccountUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Account).where(Account.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(account, key, value)
    await db.commit()
    await db.refresh(account)
    return account


@app.delete("/api/accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(account_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Account).where(Account.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    await db.delete(account)
    await db.commit()


@app.get("/api/credit-cards", response_model=list[CreditCardResponse])
async def list_credit_cards(bank_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CreditCard).where(CreditCard.bank_id == bank_id).order_by(CreditCard.created_at))
    return result.scalars().all()


@app.post("/api/credit-cards", response_model=CreditCardResponse, status_code=status.HTTP_201_CREATED)
async def create_credit_card(data: CreditCardCreate, db: AsyncSession = Depends(get_db)):
    card = CreditCard(**data.model_dump())
    db.add(card)
    await db.commit()
    await db.refresh(card)
    return card


@app.put("/api/credit-cards/{card_id}", response_model=CreditCardResponse)
async def update_credit_card(card_id: uuid.UUID, data: CreditCardUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CreditCard).where(CreditCard.id == card_id))
    card = result.scalar_one_or_none()
    if not card:
        raise HTTPException(status_code=404, detail="Credit card not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(card, key, value)
    await db.commit()
    await db.refresh(card)
    return card


@app.delete("/api/credit-cards/{card_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_credit_card(card_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CreditCard).where(CreditCard.id == card_id))
    card = result.scalar_one_or_none()
    if not card:
        raise HTTPException(status_code=404, detail="Credit card not found")
    await db.delete(card)
    await db.commit()


@app.get("/api/accounts/all", response_model=list[AccountResponse])
async def list_all_accounts(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Account).order_by(Account.created_at))
    return result.scalars().all()


@app.post("/api/transfer", response_model=TransferResponse, status_code=status.HTTP_201_CREATED)
async def transfer_between_accounts(data: TransferCreate, db: AsyncSession = Depends(get_db)):
    if data.source_account_id == data.destination_account_id:
        raise HTTPException(status_code=400, detail="Source and destination must be different")
    if data.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be greater than 0")

    result = await db.execute(select(Account).where(Account.id == data.source_account_id))
    source = result.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=404, detail="Source account not found")

    result = await db.execute(select(Account).where(Account.id == data.destination_account_id))
    destination = result.scalar_one_or_none()
    if not destination:
        raise HTTPException(status_code=404, detail="Destination account not found")

    if float(source.balance) < data.amount:
        raise HTTPException(status_code=400, detail="Insufficient balance in source account")

    source.balance = float(source.balance) - data.amount
    destination.balance = float(destination.balance) + data.amount

    desc = data.description or f"Transferencia a {destination.name}"
    source_txn = Transaction(
        bank_id=source.bank_id,
        account_id=source.id,
        type="gasto",
        amount=data.amount,
        merchant=f"Transferencia a {destination.name}",
        category="Transferencia",
        description=desc,
    )
    dest_txn = Transaction(
        bank_id=destination.bank_id,
        account_id=destination.id,
        type="ingreso",
        amount=data.amount,
        merchant=f"Transferencia desde {source.name}",
        category="Transferencia",
        description=desc,
    )
    db.add_all([source_txn, dest_txn])
    await db.commit()
    await db.refresh(source)
    await db.refresh(destination)
    await db.refresh(source_txn)
    await db.refresh(dest_txn)
    return TransferResponse(
        source=source,
        destination=destination,
        source_transaction=source_txn,
        destination_transaction=dest_txn,
    )


@app.get("/api/transactions", response_model=list[TransactionResponse])
async def list_transactions(bank_id: uuid.UUID, limit: int = 20, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Transaction).where(Transaction.bank_id == bank_id).order_by(Transaction.created_at.desc()).limit(limit)
    )
    return result.scalars().all()


@app.post("/api/transactions", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
async def create_transaction(data: TransactionCreate, db: AsyncSession = Depends(get_db)):
    if data.account_id:
        result = await db.execute(select(Account).where(Account.id == data.account_id))
        account = result.scalar_one_or_none()
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        if data.type == "gasto":
            account.balance = float(account.balance) - data.amount
        else:
            account.balance = float(account.balance) + data.amount

    if data.credit_card_id:
        result = await db.execute(select(CreditCard).where(CreditCard.id == data.credit_card_id))
        card = result.scalar_one_or_none()
        if not card:
            raise HTTPException(status_code=404, detail="Credit card not found")
        if data.type == "gasto":
            if data.currency == "USD":
                card.used_credit_usd = float(card.used_credit_usd) + data.amount
            else:
                card.used_credit = float(card.used_credit) + data.amount
        else:
            if data.currency == "USD":
                card.used_credit_usd = max(0, float(card.used_credit_usd) - data.amount)
            else:
                card.used_credit = max(0, float(card.used_credit) - data.amount)

    transaction = Transaction(**data.model_dump())
    db.add(transaction)
    await db.commit()
    await db.refresh(transaction)
    return transaction


@app.get("/api/banks/{bank_id}/rewards")
async def get_bank_rewards(bank_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Bank).where(Bank.id == bank_id))
    bank = result.scalar_one_or_none()
    if not bank:
        raise HTTPException(status_code=404, detail="Bank not found")

    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    txn_result = await db.execute(
        select(Transaction).where(
            Transaction.bank_id == bank_id,
            Transaction.created_at >= month_start,
        )
    )
    txns = txn_result.scalars().all()

    depositos = [t for t in txns if t.type == "ingreso" and t.category != "Pago tarjeta" and t.category != "Intereses"]
    compras = [t for t in txns if t.type == "gasto"]

    total_depositado = sum(float(t.amount) for t in depositos)
    tiene_deposito_50k = total_depositado >= 50000
    num_compras = len(compras)
    tiene_4_compras = num_compras >= 4

    return {
        "bank_id": str(bank_id),
        "bank_name": bank.name,
        "month": now.strftime("%Y-%m"),
        "conditions": {
            "deposito_minimo": {
                "required": 50000,
                "current": total_depositado,
                "met": tiene_deposito_50k,
            },
            "compras_minimas": {
                "required": 4,
                "current": num_compras,
                "met": tiene_4_compras,
            },
        },
        "free_maintenance": tiene_deposito_50k and tiene_4_compras,
    }
