"""Alembic environment configuration for SupplyShield.

Uses DATABASE_SYNC_URL (psycopg3 sync) for migrations.
Separate from the async DATABASE_URL used by the FastAPI app at runtime.
"""

from __future__ import annotations

import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# ── Make the app package importable from the backend/ directory ───────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Import Base and all models so Alembic can discover the full metadata.
from app.database import Base  # noqa: E402
import app.models  # noqa: E402, F401  ← registers all ORM models on Base.metadata

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _get_sync_url() -> str:
    """Return the sync DB URL, reading from env or falling back to settings default."""
    # 1. Explicit env override
    url = os.environ.get("DATABASE_SYNC_URL")
    if url:
        return url
    # 2. Derive from DATABASE_URL if set (swap async driver for sync)
    async_url = os.environ.get("DATABASE_URL", "")
    if async_url:
        return (
            async_url
            .replace("postgresql+psycopg_async://", "postgresql+psycopg://")
            .replace("postgresql+asyncpg://", "postgresql+psycopg://")
        )
    # 3. Fall back to settings default (reads .env file automatically)
    from app.config import get_settings
    return get_settings().database_sync_url


def run_migrations_offline() -> None:
    url = _get_sync_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    url = _get_sync_url()
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = url

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
