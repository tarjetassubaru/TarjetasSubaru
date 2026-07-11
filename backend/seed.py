import asyncio
from datetime import datetime, timezone
from sqlalchemy import select
from database import async_session, init_db
from models import Bank, Account
from logos_b64 import LOGO_SANTANDER, LOGO_BCI, LOGO_MP, LOGO_BANCOESTADO


async def seed():
    await init_db()
    async with async_session() as session:
        result = await session.execute(select(Bank))
        existing = result.scalars().first()
        if existing:
            print("Banks already exist, skipping seed.")
            return

        santander = Bank(name="Santander", logo=LOGO_SANTANDER, position=1)
        bci = Bank(name="Bci", logo=LOGO_BCI, position=2)
        mp = Bank(name="Mercado Pago", logo=LOGO_MP, position=3)
        bancoestado = Bank(name="BancoEstado", logo=LOGO_BANCOESTADO, position=4)

        session.add_all([santander, bci, mp, bancoestado])
        await session.flush()

        mp_account = Account(
            bank_id=mp.id,
            name="Ahorro MP",
            account_type="ahorro",
            balance=250000,
            interest_rate=5,
            color="#009ee3",
        )

        be_account = Account(
            bank_id=bancoestado.id,
            name="Ahorro Premium UF",
            account_type="ahorro_premium",
            balance=1100000,
            interest_rate=5.5,
            is_uf_indexed=True,
            deposit_date=datetime(2026, 7, 1, tzinfo=timezone.utc),
            maturity_date=datetime(2027, 3, 1, tzinfo=timezone.utc),
            withdrawals_this_year=0,
            max_free_withdrawals=3,
            color="#ff2318",
        )

        session.add_all([mp_account, be_account])
        await session.commit()
        print(f"Created banks: Santander, Bci, Mercado Pago, BancoEstado")
        print(f"Created accounts: Ahorro MP, Ahorro Premium UF")


if __name__ == "__main__":
    asyncio.run(seed())
