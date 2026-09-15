# SupplyShield

SupplyShield is a supply-chain resilience intelligence platform for turning a disruption into a clear operational decision. It connects a disruption's explainable fingerprint to historical similarity, affected shipments, financial exposure, resilience budgets, and a cascade view of risk.

## Problem and solution

Operations teams often have data about an incident but lack a fast, defensible answer to what it affects and which action deserves attention first. SupplyShield presents the path from disruption to route, shipment, cargo exposure, resilience consumption, and a recommended investigation—without presenting deterministic operational metrics as AI predictions.

## What it includes

- Executive dashboard with live aggregate RRI, active disruption counts, shipment exposure, and the Mumbai Port Crisis demo scenario.
- Disruption intelligence: summary, explainable Disruption DNA, historical similarity, affected shipments, and cascade impact.
- A deterministic Resilience Wallet for TIME, COST, TEMPERATURE, and CAPACITY, plus an explainable Resilience Remaining Index (RRI).
- Shipment investigation view and a decision-support handoff to the shipment wallet.
- PostgreSQL migrations, seed scripts, unit tests, Docker Compose, and environment-based configuration.

## Architecture

React + TypeScript/Vite provides the operations UI. FastAPI exposes typed REST endpoints and calls deterministic Python services for Disruption DNA, similarity, cascade relationships, wallet calculations, and RRI. PostgreSQL is the system of record. Optional watsonx.ai configuration is isolated in environment variables; no AI response is fabricated when credentials are absent.

```text
React dashboard → FastAPI → deterministic intelligence services → PostgreSQL
                       └→ optional watsonx.ai explanation layer (when configured)
```

See [architecture documentation](docs/architecture.md) and the [resilience-model reference](docs/resilience-model.md) for the calculation model.

## Quick start

Prerequisites: Python 3.11+, Node.js 18+, and PostgreSQL 16+ (or Docker).

```powershell
cd src
docker compose up -d

cd backend
Copy-Item ..\.env.example .env
# Update DATABASE_URL and DATABASE_SYNC_URL if your Postgres credentials differ.
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt -r requirements-dev.txt
alembic upgrade head
python scripts\seed.py --reset
uvicorn app.main:app --reload --port 8000
```

In another terminal:

```powershell
cd src\frontend
npm install
npm run dev
```

The frontend runs at `http://localhost:5173`; API documentation is at `http://localhost:8000/docs`.

## Environment variables

Copy [`src/.env.example`](src/.env.example) to `src/backend/.env`. Required local settings are `DATABASE_URL` and `DATABASE_SYNC_URL`. `WATSONX_API_KEY`, `WATSONX_PROJECT_ID`, and `WATSONX_URL` are optional and must never be committed.

## Verification

```powershell
cd src\backend
.\.venv\Scripts\python.exe -m pytest -q

cd ..\frontend
npm run build
```

## Demo flow

1. Open the dashboard to see overall RRI and disruption exposure.
2. Open **Mumbai Port Crisis** from the demo scenario CTA.
3. Review its summary, Disruption DNA, similar historical disruptions, affected shipment **S-1042**, and cascade.
4. Open S-1042's wallet from decision support to inspect RRI, four resilience dimensions, contributors, and the transaction ledger.

## API overview

| Endpoint | Purpose |
|---|---|
| `GET /health` | Service health |
| `GET /api/disruptions` | Disruption list and aggregates |
| `GET /api/disruptions/{id}` | Detail and Disruption DNA |
| `GET /api/disruptions/{id}/similar` | Deterministic historical similarity |
| `GET /api/disruptions/{id}/impact` | Affected shipments and cascade |
| `GET /api/shipments` | Operational shipment list |
| `GET /api/shipments/{id}/resilience` | Shipment wallet and explainable RRI |
| `GET /api/shipments/resilience/summary` | Network RRI summary |

## Limitations

This prototype uses seeded operational data and provides decision support only; it does not execute logistics actions. watsonx.ai is not enabled unless valid credentials are supplied. Deployment URL, demo-video URL, and team metadata remain intentionally unfilled until the team provides them.
