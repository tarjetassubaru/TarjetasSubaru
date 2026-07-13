import asyncio
from sqlalchemy import text
from database import engine


async def migrate():
    async with engine.begin() as conn:
        await conn.execute(text(
            "ALTER TABLE credit_cards ADD COLUMN IF NOT EXISTS credit_limit_usd NUMERIC(12,2) NOT NULL DEFAULT 0"
        ))
        await conn.execute(text(
            "ALTER TABLE credit_cards ADD COLUMN IF NOT EXISTS used_credit_usd NUMERIC(12,2) NOT NULL DEFAULT 0"
        ))
        await conn.execute(text(
            "ALTER TABLE transactions ADD COLUMN IF NOT EXISTS currency VARCHAR(3) NOT NULL DEFAULT 'CLP'"
        ))
    print("Migration completed: added USD fields to credit_cards, currency to transactions")


if __name__ == "__main__":
    asyncio.run(migrate())
