"""Database integration tests.

These tests require a live database (DATABASE_SYNC_URL env var).
They are skipped automatically if the database is not available.
"""

from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session

# ── Skip all tests in this module if DATABASE_SYNC_URL is not configured ─────
DATABASE_SYNC_URL = os.environ.get("DATABASE_SYNC_URL", "")
if not DATABASE_SYNC_URL:
    try:
        from dotenv import load_dotenv
        load_dotenv()
        DATABASE_SYNC_URL = os.environ.get("DATABASE_SYNC_URL", "")
    except ImportError:
        pass

pytestmark = pytest.mark.skipif(
    not DATABASE_SYNC_URL,
    reason="DATABASE_SYNC_URL not set — skipping database tests",
)


@pytest.fixture(scope="module")
def db_engine():
    engine = create_engine(DATABASE_SYNC_URL, echo=False)
    yield engine
    engine.dispose()


@pytest.fixture(scope="module")
def db_session(db_engine):
    with Session(db_engine) as session:
        yield session


# ── Schema tests ──────────────────────────────────────────────────────────────

EXPECTED_TABLES = [
    "suppliers", "shipments", "disruptions", "shipment_disruptions",
    "routes", "fleet_vehicles", "cold_chain_readings",
    "resilience_wallets", "resilience_transactions",
    "rri_snapshots", "recovery_plans", "approvals",
    "audit_log", "simulation_runs",
]


def test_database_connection(db_engine):
    with db_engine.connect() as conn:
        result = conn.execute(text("SELECT 1")).scalar()
    assert result == 1


def test_alembic_version_table_exists(db_engine):
    insp = inspect(db_engine)
    assert "alembic_version" in insp.get_table_names()


@pytest.mark.parametrize("table_name", EXPECTED_TABLES)
def test_table_exists(db_engine, table_name):
    insp = inspect(db_engine)
    assert table_name in insp.get_table_names(), f"Table '{table_name}' missing from schema"


# ── Seed data count tests ─────────────────────────────────────────────────────

def test_suppliers_count(db_session):
    n = db_session.execute(text("SELECT COUNT(*) FROM suppliers")).scalar()
    assert n >= 20, f"Expected >=20 suppliers, got {n}"


def test_shipments_count(db_session):
    n = db_session.execute(text("SELECT COUNT(*) FROM shipments")).scalar()
    assert n >= 500, f"Expected >=500 shipments, got {n}"


def test_fleet_vehicles_count(db_session):
    n = db_session.execute(text("SELECT COUNT(*) FROM fleet_vehicles")).scalar()
    assert n >= 50, f"Expected >=50 fleet vehicles, got {n}"


def test_routes_count(db_session):
    n = db_session.execute(text("SELECT COUNT(*) FROM routes")).scalar()
    assert n >= 40, f"Expected >=40 routes, got {n}"


def test_disruptions_count(db_session):
    n = db_session.execute(text("SELECT COUNT(*) FROM disruptions")).scalar()
    assert n >= 30, f"Expected >=30 disruptions, got {n}"


def test_cold_chain_readings_exceed_100k(db_session):
    n = db_session.execute(text("SELECT COUNT(*) FROM cold_chain_readings")).scalar()
    assert n >= 100_000, f"Expected >=100,000 cold-chain readings, got {n:,}"


# ── Demo record tests ─────────────────────────────────────────────────────────

def test_s1042_exists(db_session):
    row = db_session.execute(
        text("SELECT shipment_code, origin, destination, cargo_type, "
             "temperature_sensitive, priority, status "
             "FROM shipments WHERE shipment_code = 'S-1042'")
    ).fetchone()
    assert row is not None, "S-1042 not found in database"
    assert row.origin == "Ahmedabad"
    assert row.destination == "Dubai"
    assert row.cargo_type == "Pharmaceutical"
    assert row.temperature_sensitive is True
    assert row.priority.lower() == "critical"
    assert row.status.lower() == "at_risk"


def test_s1042_has_temperature_readings(db_session):
    n = db_session.execute(
        text("""SELECT COUNT(*) FROM cold_chain_readings ccr
                JOIN shipments s ON s.id = ccr.shipment_id
                WHERE s.shipment_code = 'S-1042'""")
    ).scalar()
    assert n > 0, "S-1042 has no cold-chain readings"
    assert n >= 100, f"S-1042 has only {n} readings (expected >=100)"


def test_s1042_has_temperature_excursion(db_session):
    row = db_session.execute(
        text("""SELECT COUNT(*) as breach_count, MAX(temperature_c) as max_temp
                FROM cold_chain_readings ccr
                JOIN shipments s ON s.id = ccr.shipment_id
                WHERE s.shipment_code = 'S-1042' AND ccr.is_breach = true""")
    ).fetchone()
    assert row.breach_count > 0, "S-1042 has no breach readings — excursion missing"
    assert float(row.max_temp) > 8.0, f"S-1042 max temp is {row.max_temp}°C — excursion not recorded"
    assert float(row.max_temp) < 15.0, f"S-1042 excursion temp {row.max_temp}°C is implausibly high"


def test_t101_exists(db_session):
    row = db_session.execute(
        text("SELECT vehicle_code, current_location, status, refrigerated "
             "FROM fleet_vehicles WHERE vehicle_code = 'T-101'")
    ).fetchone()
    assert row is not None, "T-101 not found in database"
    assert "Ahmedabad" in row.current_location
    assert row.status.lower() == "available"
    assert row.refrigerated is True


def test_mumbai_port_crisis_exists(db_session):
    row = db_session.execute(
        text("SELECT disruption_code, name, severity, status, type "
             "FROM disruptions WHERE disruption_code = 'DIS-001'")
    ).fetchone()
    assert row is not None, "DIS-001 (Mumbai Port Crisis) not found"
    assert "Mumbai Port" in row.name
    assert row.severity >= 7
    assert row.status.lower() == "active"
    assert row.type.lower() == "port"


def test_s1042_linked_to_mumbai_port_crisis(db_session):
    row = db_session.execute(
        text("""SELECT sd.impact_score, sd.delay_hours
                FROM shipment_disruptions sd
                JOIN shipments s ON s.id = sd.shipment_id
                JOIN disruptions d ON d.id = sd.disruption_id
                WHERE s.shipment_code = 'S-1042'
                  AND d.disruption_code = 'DIS-001'""")
    ).fetchone()
    assert row is not None, "S-1042 not linked to DIS-001 (Mumbai Port Crisis)"
    assert row.impact_score > 0.5, f"Impact score too low: {row.impact_score}"
    assert row.delay_hours >= 24, f"Delay too short: {row.delay_hours}h"


def test_historical_disruptions_for_dna_library(db_session):
    n = db_session.execute(
        text("SELECT COUNT(*) FROM disruptions WHERE status = 'HISTORICAL'")
    ).scalar()
    assert n >= 5, f"Need >=5 historical disruptions for DNA library, got {n}"


def test_resilience_wallets_created(db_session):
    n = db_session.execute(text("SELECT COUNT(*) FROM resilience_wallets")).scalar()
    assert n > 0, "No resilience wallets found"
    # Four dimensions × 20 suppliers + 4 system = 84
    assert n >= 80, f"Expected >=80 wallets, got {n}"


def test_audit_log_has_seed_entries(db_session):
    n = db_session.execute(
        text("SELECT COUNT(*) FROM audit_log WHERE source = 'seed'")
    ).scalar()
    assert n > 0, "No audit log entries from seed"
