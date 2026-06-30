"""
db/database.py
───────────────
Async SQLAlchemy engine + session factory.

NullPool is required here because this app has TWO separate asyncio
event loops running in different threads:
  1. FastAPI's main loop (serves the dashboard API)
  2. FrameProcessor's dedicated loop (calls save_event from the camera thread)

asyncpg connections are bound to the event loop that created them.
A pooled connection created on loop A will crash with
"attached to a different loop" if reused from loop B.
NullPool opens a fresh connection per request instead of reusing one
from a pool, which avoids this cross-loop binding entirely.
"""

import logging

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from config.settings import settings
from db.models import Base

logger = logging.getLogger(__name__)

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    poolclass=NullPool,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db() -> None:
    """Create all tables if not exists."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialized [OK]")


async def get_session() -> AsyncSession:
    """FastAPI dependency — yield db session."""
    async with AsyncSessionLocal() as session:
        yield session