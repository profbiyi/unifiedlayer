"""
Async database layer (SQLAlchemy 2.0 + asyncpg).

This runs ALONGSIDE the synchronous engine in database.py during the incremental
migration to fully-async request handling. Routers are moved over one slice at a
time: a handler that depends on `get_async_db` is async end-to-end (asyncpg, no
event-loop blocking); everything else keeps using the sync `get_db` until migrated.

The async URL is derived from the same DATABASE_URL (driver swapped to asyncpg, or
aiosqlite for a sqlite test DB), so there is a single source of truth for the DSN.
"""
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.config import settings


def _to_async_url(url: str) -> str:
    """Translate a sync SQLAlchemy URL to its async driver equivalent."""
    if url.startswith("postgresql+asyncpg://"):
        return url
    if url.startswith("postgresql+psycopg2://"):
        return url.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("sqlite+aiosqlite://"):
        return url
    if url.startswith("sqlite://"):
        return url.replace("sqlite://", "sqlite+aiosqlite://", 1)
    return url


ASYNC_DATABASE_URL = _to_async_url(settings.DATABASE_URL)

_is_sqlite = ASYNC_DATABASE_URL.startswith("sqlite")

# asyncpg manages its own pool; mirror the sync pool sizing for Postgres. SQLite
# (tests) takes neither pool sizing nor server_settings.
_engine_kwargs = {"echo": settings.DATABASE_ECHO, "pool_pre_ping": True}
if not _is_sqlite:
    _engine_kwargs.update(
        pool_size=settings.DATABASE_POOL_SIZE,
        max_overflow=settings.DATABASE_MAX_OVERFLOW,
        pool_recycle=3600,
        connect_args={"server_settings": {"timezone": "UTC"}},
    )

async_engine = create_async_engine(ASYNC_DATABASE_URL, **_engine_kwargs)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    autoflush=False,
    expire_on_commit=False,
)


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding an AsyncSession (async-migrated routes)."""
    async with AsyncSessionLocal() as session:
        yield session
