"""Async SQLAlchemy database engine and session management.

The engine is created lazily on first use: if asyncpg is not installed or
the DATABASE_URL is unreachable, the application still starts and the
/health endpoint works normally. Only DB-dependent routes will fail.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING

from sqlalchemy.orm import DeclarativeBase

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""


# ── Lazy engine / session-factory ─────────────────────────────────────────────
# We don't create the engine at import time so that:
#   1. Tests that never touch the DB can import app modules without asyncpg.
#   2. The application starts up even when PostgreSQL is not yet reachable.

_engine = None
_AsyncSessionLocal = None


def _get_engine():
    global _engine
    if _engine is None:
        from sqlalchemy.ext.asyncio import create_async_engine

        from app.config import get_settings

        settings = get_settings()
        _engine = create_async_engine(
            settings.database_url,
            echo=settings.debug,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
        )
    return _engine


def _get_session_factory():
    global _AsyncSessionLocal
    if _AsyncSessionLocal is None:
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

        _AsyncSessionLocal = async_sessionmaker(
            bind=_get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
        )
    return _AsyncSessionLocal


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a DB session per request."""
    factory = _get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
