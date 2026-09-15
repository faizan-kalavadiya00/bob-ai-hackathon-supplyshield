# SupplyShield — Source Code

All project source code lives in this directory.

```
src/
├── backend/           ← FastAPI Python backend
│   ├── app/           ← Application package
│   │   ├── models/    ← SQLAlchemy ORM models (14 tables)
│   │   ├── schemas/   ← Pydantic schemas (Phase 3)
│   │   ├── routers/   ← FastAPI route handlers
│   │   └── services/  ← Business logic (Phase 2+)
│   ├── migrations/    ← Alembic migration scripts
│   ├── scripts/       ← seed.py, verify_seed.py, verify_tables.py
│   └── tests/         ← pytest test suite
├── frontend/          ← React + TypeScript + Vite frontend
├── docker-compose.yml ← PostgreSQL service (local dev)
└── .env.example       ← Environment variable template
```

---

## Prerequisites

- Python 3.11+ (tested on 3.14)
- Node.js 18+
- PostgreSQL 16+ (running locally **or** via Docker)

---

## Quick Start

### Option A — PostgreSQL via Docker

```bash
cd src
docker compose up -d        # starts PostgreSQL on port 5432
```

### Option B — Existing local PostgreSQL

Ensure a `supplyshield` database exists and you have credentials.

---

### 1 — Configure environment

```bash
cd src/backend
cp ../.env.example .env
# Edit .env — set DATABASE_URL and DATABASE_SYNC_URL with your credentials
```

`.env` example (never committed):
```
DATABASE_URL=postgresql+psycopg_async://postgres:<password>@localhost:5432/supplyshield
DATABASE_SYNC_URL=postgresql+psycopg://postgres:<password>@localhost:5432/supplyshield
```

### 2 — Install backend dependencies

```bash
cd src/backend
python -m venv .venv
source .venv/bin/activate       # macOS/Linux
# .\.venv\Scripts\activate      # Windows PowerShell

pip install -r requirements.txt -r requirements-dev.txt
```

### 3 — Run database migrations

```bash
cd src/backend
alembic upgrade head
```

### 4 — Seed the database

```bash
cd src/backend
python scripts/seed.py --reset
```

This creates:
- 20 suppliers, 40 routes, 30 disruptions
- 500 shipments, 50 fleet vehicles
- 174,000+ cold-chain sensor readings
- Demo records: **S-1042**, **T-101**, **DIS-001** (Mumbai Port Crisis)

### 5 — Verify seed data

```bash
cd src/backend
python scripts/verify_seed.py
```

### 6 — Run the backend

```bash
cd src/backend
uvicorn app.main:app --reload --port 8000
```

Backend: http://localhost:8000  
API docs: http://localhost:8000/docs

### 7 — Start the frontend

```bash
cd src/frontend
npm install
npm run dev
```

Frontend: http://localhost:5173

---

## Backend Tests

```bash
cd src/backend
pytest -v                          # unit tests only (no DB needed)
DATABASE_SYNC_URL=postgresql+psycopg://postgres:<pw>@localhost:5432/supplyshield \
  pytest -v                        # includes database integration tests
```

## Frontend Build Check

```bash
cd src/frontend
npm run build
```

---

## Reproduce the Database from Scratch

```bash
# 1. Start PostgreSQL (or use existing)
cd src && docker compose up -d

# 2. Run migrations
cd src/backend
DATABASE_SYNC_URL=postgresql+psycopg://postgres:<pw>@localhost:5432/supplyshield \
  alembic upgrade head

# 3. Seed data
DATABASE_SYNC_URL=postgresql+psycopg://postgres:<pw>@localhost:5432/supplyshield \
  python scripts/seed.py --reset

# 4. Verify
DATABASE_SYNC_URL=postgresql+psycopg://postgres:<pw>@localhost:5432/supplyshield \
  python scripts/verify_seed.py
```

---

## Environment Variables

See [`.env.example`](.env.example) for all variables.  
The application runs without watsonx.ai credentials — AI features gracefully degrade.
