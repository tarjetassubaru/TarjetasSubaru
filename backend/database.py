import os
import ssl as ssl_mod
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "")

# Neon requires SSL
if DATABASE_URL and "neon.tech" in DATABASE_URL:
    # asyncpg uses its own SSL arg, not sslmode from the URL
    DATABASE_URL = DATABASE_URL.replace("?sslmode=require", "")
    ssl_context = ssl_mod.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl_mod.CERT_NONE
    engine = create_async_engine(DATABASE_URL, echo=False, connect_args={"ssl": ssl_context})
elif DATABASE_URL:
    engine = create_async_engine(DATABASE_URL, echo=False)
else:
    raise RuntimeError("DATABASE_URL environment variable is not set! Go to Railway > Variables and add it.")

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with async_session() as session:
        yield session


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
