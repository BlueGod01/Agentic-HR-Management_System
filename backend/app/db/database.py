"""
Database engine - async SQLAlchemy
Supports SQLite (dev) and PostgreSQL (prod) via DATABASE_URL in .env
"""
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import event
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# ── Engine setup ──────────────────────────────────────────────────────────────

connect_args = {}
if settings.is_sqlite:
    connect_args = {"check_same_thread": False}

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    connect_args=connect_args,
    pool_pre_ping=True,
    pool_recycle=300 if not settings.is_sqlite else -1,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


# ── Base model ────────────────────────────────────────────────────────────────

class Base(DeclarativeBase):
    pass


# ── Dependency ────────────────────────────────────────────────────────────────

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ── Init DB ───────────────────────────────────────────────────────────────────

async def init_db() -> None:
    """Create all tables on startup"""
    from app.models import user, employee, alert, chat_log, policy  # noqa: F401
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables initialized")
