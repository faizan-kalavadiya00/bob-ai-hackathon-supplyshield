"""Verify all demo records exist and meet requirements.

Usage:
    DATABASE_SYNC_URL=postgresql+psycopg://postgres:<pw>@localhost:5432/supplyshield \
        python scripts/verify_seed.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.models import ColdChainReading, Disruption, FleetVehicle, Shipment, Supplier


def check(label: str, passed: bool, detail: str = "") -> bool:
    status = "PASS" if passed else "FAIL"
    suffix = f"  ({detail})" if detail else ""
    print(f"  [{status}] {label}{suffix}")
    return passed


def main() -> None:
    url = os.environ.get("DATABASE_SYNC_URL", "")
    if not url:
        load_dotenv()
        url = os.environ.get("DATABASE_SYNC_URL", "")
    if not url:
        print("ERROR: DATABASE_SYNC_URL not set.")
        sys.exit(1)

    engine = create_engine(url, echo=False)
    all_passed = True

    with Session(engine) as session:
        print("\n=== Table row counts ===")
        tables = [
            "suppliers", "routes", "disruptions", "fleet_vehicles",
            "shipments", "shipment_disruptions", "cold_chain_readings",
            "resilience_wallets", "resilience_transactions",
            "rri_snapshots", "recovery_plans", "approvals",
            "audit_log", "simulation_runs",
        ]
        for t in tables:
            n = session.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar()
            print(f"  {t:30s}: {n:>8,}")

        print("\n=== Required record counts ===")
        n_sup = session.execute(text("SELECT COUNT(*) FROM suppliers")).scalar()
        all_passed &= check("suppliers >= 20", n_sup >= 20, str(n_sup))

        n_ship = session.execute(text("SELECT COUNT(*) FROM shipments")).scalar()
        all_passed &= check("shipments >= 500", n_ship >= 500, str(n_ship))

        n_fleet = session.execute(text("SELECT COUNT(*) FROM fleet_vehicles")).scalar()
        all_passed &= check("fleet_vehicles >= 50", n_fleet >= 50, str(n_fleet))

        n_routes = session.execute(text("SELECT COUNT(*) FROM routes")).scalar()
        all_passed &= check("routes >= 40", n_routes >= 40, str(n_routes))

        n_dis = session.execute(text("SELECT COUNT(*) FROM disruptions")).scalar()
        all_passed &= check("disruptions >= 30", n_dis >= 30, str(n_dis))

        n_cc = session.execute(text("SELECT COUNT(*) FROM cold_chain_readings")).scalar()
        all_passed &= check("cold_chain_readings >= 100,000", n_cc >= 100_000, f"{n_cc:,}")

        print("\n=== Demo record S-1042 ===")
        s1042 = session.query(Shipment).filter_by(shipment_code="S-1042").first()
        all_passed &= check("S-1042 exists", s1042 is not None)
        if s1042:
            all_passed &= check("S-1042 origin = Ahmedabad",
                                s1042.origin == "Ahmedabad", s1042.origin)
            all_passed &= check("S-1042 destination = Dubai",
                                s1042.destination == "Dubai", s1042.destination)
            all_passed &= check("S-1042 cargo = Pharmaceutical",
                                s1042.cargo_type == "Pharmaceutical", s1042.cargo_type)
            all_passed &= check("S-1042 temp_sensitive = True",
                                s1042.temperature_sensitive is True)
            all_passed &= check("S-1042 min_temp = 2.0°C",
                                s1042.min_temperature_c == 2.0, str(s1042.min_temperature_c))
            all_passed &= check("S-1042 max_temp = 8.0°C",
                                s1042.max_temperature_c == 8.0, str(s1042.max_temperature_c))
            all_passed &= check("S-1042 priority = CRITICAL",
                                s1042.priority.value == "critical", s1042.priority.value)
            all_passed &= check("S-1042 status = AT_RISK",
                                s1042.status.value == "at_risk", s1042.status.value)
            all_passed &= check("S-1042 value > $400k",
                                float(s1042.cargo_value_usd) > 400000,
                                f"${float(s1042.cargo_value_usd):,.0f}")

            n_s1042_readings = session.query(ColdChainReading).filter_by(
                shipment_id=s1042.id
            ).count()
            all_passed &= check("S-1042 has cold-chain readings",
                                n_s1042_readings > 0, str(n_s1042_readings))

            n_s1042_breach = session.query(ColdChainReading).filter_by(
                shipment_id=s1042.id, is_breach=True
            ).count()
            all_passed &= check("S-1042 has temperature excursion (breach readings)",
                                n_s1042_breach > 0, f"{n_s1042_breach} breach readings")

            max_temp = session.execute(
                text("SELECT MAX(temperature_c) FROM cold_chain_readings WHERE shipment_id = :sid"),
                {"sid": s1042.id},
            ).scalar()
            all_passed &= check("S-1042 max observed temp > 8.0°C (excursion confirmed)",
                                float(max_temp) > 8.0, f"{max_temp}°C")
            all_passed &= check("S-1042 excursion not absurd (max < 15°C)",
                                float(max_temp) < 15.0, f"{max_temp}°C")

        print("\n=== Demo record T-101 ===")
        t101 = session.query(FleetVehicle).filter_by(vehicle_code="T-101").first()
        all_passed &= check("T-101 exists", t101 is not None)
        if t101:
            all_passed &= check("T-101 location = Ahmedabad",
                                "Ahmedabad" in t101.current_location, t101.current_location)
            all_passed &= check("T-101 status = AVAILABLE",
                                t101.status.value == "available", t101.status.value)
            all_passed &= check("T-101 refrigerated = True",
                                t101.refrigerated is True)

        print("\n=== Demo disruption: Mumbai Port Crisis ===")
        crisis = session.query(Disruption).filter_by(
            disruption_code="DIS-001"
        ).first()
        all_passed &= check("Mumbai Port Crisis (DIS-001) exists", crisis is not None)
        if crisis:
            all_passed &= check("name contains 'Mumbai Port'",
                                "Mumbai Port" in crisis.name, crisis.name)
            all_passed &= check("severity >= 7 (high)",
                                crisis.severity >= 7, str(crisis.severity))
            all_passed &= check("status = ACTIVE",
                                crisis.status.value == "active", crisis.status.value)
            all_passed &= check("type = PORT",
                                crisis.type.value == "port", crisis.type.value)
            # Check expected ~48h duration in description or end_time
            all_passed &= check("description mentions strike",
                                "strike" in (crisis.description or "").lower(),
                                crisis.description[:60] if crisis.description else "")

        print("\n=== Historical disruptions (DNA library) ===")
        n_historical = session.query(Disruption).filter_by(
            status="HISTORICAL"
        ).count()
        all_passed &= check("historical disruption records >= 5", n_historical >= 5,
                            str(n_historical))
        prior_mumbai = session.query(Disruption).filter_by(
            disruption_code="DIS-006"
        ).first()
        all_passed &= check("Prior Mumbai Port Strike (DIS-006) exists",
                            prior_mumbai is not None)

        print("\n=== Shipment-disruption links ===")
        s1042_links = session.execute(
            text("""SELECT d.name, sd.impact_score, sd.delay_hours
                    FROM shipment_disruptions sd
                    JOIN disruptions d ON d.id = sd.disruption_id
                    JOIN shipments s ON s.id = sd.shipment_id
                    WHERE s.shipment_code = 'S-1042'""")
        ).fetchall()
        all_passed &= check("S-1042 linked to disruptions",
                            len(s1042_links) > 0, f"{len(s1042_links)} disruptions")
        for row in s1042_links:
            print(f"    -> {row[0]}: impact={row[1]}, delay={row[2]}h")

        print("\n=== Resilience wallets ===")
        n_wallets = session.execute(text("SELECT COUNT(*) FROM resilience_wallets")).scalar()
        all_passed &= check("Resilience wallets created", n_wallets > 0, str(n_wallets))
        n_transactions = session.execute(
            text("SELECT COUNT(*) FROM resilience_transactions")
        ).scalar()
        all_passed &= check("Resilience transactions created",
                            n_transactions > 0, str(n_transactions))

    print(f"\n{'='*45}")
    if all_passed:
        print("ALL CHECKS PASSED")
    else:
        print("SOME CHECKS FAILED — review output above")
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
