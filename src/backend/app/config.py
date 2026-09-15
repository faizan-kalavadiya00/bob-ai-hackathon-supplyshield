"""Application configuration via pydantic-settings.

All settings are loaded from environment variables (or a .env file).
Defaults are safe for local development without any external services.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ───────────────────────────────────────────────────────────────────
    app_name: str = "SupplyShield"
    app_version: str = "0.1.0"
    app_env: Literal["development", "staging", "production"] = "development"
    app_port: int = Field(default=8000, ge=1, le=65535)
    debug: bool = True

    # ── Database ──────────────────────────────────────────────────────────────
    # When DATABASE_URL is not set the app starts fine; DB-dependent routes
    # will surface a 503 rather than crashing at startup.
    # Async URL for the FastAPI app (psycopg3 async driver — no C compilation needed).
    # Override in .env — default is for local development with postgres superuser.
    database_url: str = Field(
        default="postgresql+psycopg_async://postgres:postgres@localhost:5432/supplyshield",
        description="Async SQLAlchemy URL (psycopg3 async driver)",
    )
    # Sync URL for Alembic migrations and the seed script.
    database_sync_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/supplyshield",
        description="Sync SQLAlchemy URL (psycopg3 sync driver)",
    )

    # ── CORS ──────────────────────────────────────────────────────────────────
    # Comma-separated list of allowed origins for the API.
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    # ── IBM watsonx.ai (optional) ─────────────────────────────────────────────
    watsonx_api_key: str = ""
    watsonx_project_id: str = ""
    watsonx_url: str = "https://us-south.ml.cloud.ibm.com"

    @property
    def watsonx_enabled(self) -> bool:
        return bool(self.watsonx_api_key and self.watsonx_project_id)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached Settings singleton."""
    return Settings()
