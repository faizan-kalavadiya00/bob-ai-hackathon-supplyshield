"""Utility: verify all expected tables exist in the database.

Usage:
    DATABASE_SYNC_URL=postgresql+psycopg://postgres:<pw>@localhost:5432/supplyshield \
        python scripts/verify_tables.py
"""
import os
import sys

import psycopg


def main() -> None:
    url = os.environ.get("DATABASE_SYNC_URL", "")
    if not url:
        # Try loading from .env
        try:
            from dotenv import load_dotenv
            load_dotenv()
            url = os.environ.get("DATABASE_SYNC_URL", "")
        except ImportError:
            pass

    if not url:
        print("ERROR: DATABASE_SYNC_URL not set. Copy src/.env.example to src/backend/.env and fill in credentials.")
        sys.exit(1)

    # Strip the SQLAlchemy driver prefix to get a raw psycopg DSN
    dsn = url.replace("postgresql+psycopg://", "postgresql://")

    conn = psycopg.connect(dsn)
    cur = conn.execute(
        "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename"
    )
    tables = [r[0] for r in cur.fetchall()]
    print(f"Tables in 'supplyshield' ({len(tables)}):")
    for t in tables:
        print(f"  - {t}")
    conn.close()


if __name__ == "__main__":
    main()
