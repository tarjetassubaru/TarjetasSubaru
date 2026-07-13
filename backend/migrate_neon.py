import asyncio
import os
import ssl as ssl_mod
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "")

if not DATABASE_URL:
    print("DATABASE_URL not set, skipping migration")
    exit(0)

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgresql://") and "+asyncpg" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

DATABASE_URL = DATABASE_URL.replace("?sslmode=require", "")

if "neon.tech" in DATABASE_URL:
    ssl_context = ssl_mod.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl_mod.CERT_NONE
    engine = create_async_engine(DATABASE_URL, echo=False, connect_args={"ssl": ssl_context})
else:
    engine = create_async_engine(DATABASE_URL, echo=False)


async def migrate():
    print(f"Running migration...")
    async with engine.begin() as conn:
        await conn.execute(text(
            "ALTER TABLE credit_cards ADD COLUMN IF NOT EXISTS credit_limit_usd NUMERIC(12,2) NOT NULL DEFAULT 0"
        ))
        print("  Added credit_limit_usd column")
        await conn.execute(text(
            "ALTER TABLE credit_cards ADD COLUMN IF NOT EXISTS used_credit_usd NUMERIC(12,2) NOT NULL DEFAULT 0"
        ))
        print("  Added used_credit_usd column")
        await conn.execute(text(
            "ALTER TABLE transactions ADD COLUMN IF NOT EXISTS currency VARCHAR(3) NOT NULL DEFAULT 'CLP'"
        ))
        print("  Added currency column")
        await conn.execute(text(
            "UPDATE credit_cards SET credit_limit_usd = 70, used_credit_usd = 10.66 WHERE name ILIKE '%bci%' OR name ILIKE '%gold%'"
        ))
        print("  Updated BCI card USD values")
    print("Migration completed successfully")


if __name__ == "__main__":
    asyncio.run(migrate())
