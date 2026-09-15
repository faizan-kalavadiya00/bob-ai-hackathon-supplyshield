"""SupplyShield deterministic seed script.

Populates the database with realistic, internally consistent demo data.
All randomness uses a fixed seed (SEED = 42) so results are reproducible.

Usage:
    DATABASE_SYNC_URL=postgresql+psycopg://postgres:<pw>@localhost:5432/supplyshield \\
        python scripts/seed.py [--reset]

    --reset  drops and re-inserts all seed data (idempotent)
"""

from __future__ import annotations

import argparse
import os
import random
import sys
from datetime import datetime, timedelta, timezone

# ── Allow importing app modules ───────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.models import (  # noqa: F401 – registers all on Base.metadata
    AuditLog,
    Approval,
    ColdChainReading,
    Disruption,
    FleetVehicle,
    RecoveryPlan,
    ResilienceTransaction,
    ResilienceWallet,
    RRISnapshot,
    Route,
    ShipmentDisruption,
    Shipment,
    SimulationRun,
    Supplier,
)
from app.models.disruption import DisruptionStatus, DisruptionType
from app.models.fleet import VehicleStatus
from app.models.resilience import WalletDimension
from app.models.shipment import CargoPriority, ShipmentStatus
from app.services.disruption_impact import apply_disruption_to_shipment
from app.services.wallet_service import initialise_shipment_wallets

# ─────────────────────────────────────────────────────────────────────────────
SEED = 42
rng = random.Random(SEED)

NOW = datetime(2026, 9, 15, 12, 0, 0, tzinfo=timezone.utc)

# ─────────────────────────────────────────────────────────────────────────────
# Reference data tables
# ─────────────────────────────────────────────────────────────────────────────

SUPPLIER_DATA = [
    # (code, name, country, city, reliability, lead_days, tier)
    ("SUP-001", "Ahmedabad Pharma Exports",  "India",        "Ahmedabad",    0.94, 3,  1),
    ("SUP-002", "Mumbai Chemical Corp",       "India",        "Mumbai",       0.88, 4,  1),
    ("SUP-003", "Delhi Electronics Hub",      "India",        "New Delhi",    0.91, 5,  1),
    ("SUP-004", "Chennai Auto Parts Ltd",     "India",        "Chennai",      0.86, 6,  2),
    ("SUP-005", "Kolkata Textiles Group",     "India",        "Kolkata",      0.83, 7,  2),
    ("SUP-006", "Bangalore Tech Supplies",    "India",        "Bangalore",    0.92, 4,  1),
    ("SUP-007", "Surat Textile Mills",        "India",        "Surat",        0.79, 8,  2),
    ("SUP-008", "Pune Engineering Works",     "India",        "Pune",         0.87, 5,  2),
    ("SUP-009", "Hyderabad Pharma Co",        "India",        "Hyderabad",    0.93, 3,  1),
    ("SUP-010", "Kochi Marine Products",      "India",        "Kochi",        0.82, 6,  2),
    ("SUP-011", "Dubai Global Trading",       "UAE",          "Dubai",        0.95, 2,  1),
    ("SUP-012", "Singapore Logistics Hub",    "Singapore",    "Singapore",    0.97, 2,  1),
    ("SUP-013", "London Commodities Ltd",     "UK",           "London",       0.90, 10, 2),
    ("SUP-014", "Frankfurt Manufacturing",    "Germany",      "Frankfurt",    0.93, 8,  1),
    ("SUP-015", "Shanghai Import Export",     "China",        "Shanghai",     0.85, 12, 2),
    ("SUP-016", "Tokyo Precision Parts",      "Japan",        "Tokyo",        0.96, 9,  1),
    ("SUP-017", "New York Commodities",       "USA",          "New York",     0.89, 14, 2),
    ("SUP-018", "Jaipur Handicrafts",         "India",        "Jaipur",       0.76, 9,  3),
    ("SUP-019", "Nagpur Agro Products",       "India",        "Nagpur",       0.80, 7,  3),
    ("SUP-020", "Vizag Steel Suppliers",      "India",        "Visakhapatnam",0.84, 6,  2),
]

# Hub network: (code, name, lat, lon)
HUBS = {
    "AMD": ("Ahmedabad",     23.0225, 72.5714),
    "BOM": ("Mumbai",        19.0760, 72.8777),
    "DEL": ("New Delhi",     28.6139, 77.2090),
    "MAA": ("Chennai",       13.0827, 80.2707),
    "CCU": ("Kolkata",       22.5726, 88.3639),
    "BLR": ("Bangalore",     12.9716, 77.5946),
    "HYD": ("Hyderabad",     17.3850, 78.4867),
    "COK": ("Kochi",         9.9312,  76.2673),
    "PNQ": ("Pune",          18.5204, 73.8567),
    "STV": ("Surat",         21.1702, 72.8311),
    "DXB": ("Dubai",         25.2048, 55.2708),
    "SIN": ("Singapore",     1.3521,  103.8198),
    "LHR": ("London",        51.5074, -0.1278),
    "FRA": ("Frankfurt",     50.1109, 8.6821),
    "PVG": ("Shanghai",      31.2304, 121.4737),
    "NRT": ("Tokyo",         35.6762, 139.6503),
    "JFK": ("New York",      40.7128, -74.0060),
}

# Routes: (code, name, origin_hub, dest_hub, km, hours, risk, cap_kg, primary, mode)
ROUTE_DATA = [
    ("RT-001", "Ahmedabad–Mumbai Road",     "AMD", "BOM",  530,   9.0, 0.15, 25000, True,  "road"),
    ("RT-002", "Ahmedabad–Mumbai Rail",     "AMD", "BOM",  530,  11.0, 0.10, 50000, False, "rail"),
    ("RT-003", "Mumbai–Dubai Sea",          "BOM", "DXB", 1970,  80.0, 0.20, 500000, True,  "sea"),
    ("RT-004", "Mumbai–Dubai Air",          "BOM", "DXB", 1970,   4.0, 0.12, 10000, False, "air"),
    ("RT-005", "Mumbai–Singapore Sea",      "BOM", "SIN", 4300, 168.0, 0.25, 800000, True,  "sea"),
    ("RT-006", "Mumbai–London Sea",         "BOM", "LHR",11000, 360.0, 0.30, 600000, True,  "sea"),
    ("RT-007", "Mumbai–London Air",         "BOM", "LHR",11000,  10.0, 0.18, 12000, False, "air"),
    ("RT-008", "Delhi–Mumbai Road",         "DEL", "BOM",1400,  22.0, 0.22, 20000, True,  "road"),
    ("RT-009", "Delhi–Frankfurt Air",       "DEL", "FRA",6200,   8.5, 0.15, 10000, True,  "air"),
    ("RT-010", "Chennai–Singapore Sea",     "MAA", "SIN",2900, 120.0, 0.20, 600000, True,  "sea"),
    ("RT-011", "Chennai–Dubai Sea",         "MAA", "DXB",2900, 110.0, 0.22, 500000, False, "sea"),
    ("RT-012", "Bangalore–Dubai Air",       "BLR", "DXB",2400,   4.5, 0.12, 8000, True,  "air"),
    ("RT-013", "Hyderabad–Singapore Air",   "HYD", "SIN",5600,   6.0, 0.14, 9000, True,  "air"),
    ("RT-014", "Kochi–Dubai Sea",           "COK", "DXB",2600, 100.0, 0.18, 450000, True,  "sea"),
    ("RT-015", "Kolkata–Shanghai Sea",      "CCU", "PVG",3200, 132.0, 0.28, 550000, True,  "sea"),
    ("RT-016", "Mumbai–Shanghai Sea",       "BOM", "PVG",6200, 240.0, 0.25, 700000, True,  "sea"),
    ("RT-017", "Delhi–Tokyo Air",           "DEL", "NRT",5800,   9.0, 0.16, 10000, True,  "air"),
    ("RT-018", "Mumbai–New York Sea",       "BOM", "JFK",13000, 480.0, 0.35, 500000, True,  "sea"),
    ("RT-019", "Mumbai–New York Air",       "BOM", "JFK",13000,  16.0, 0.20, 15000, False, "air"),
    ("RT-020", "Ahmedabad–Delhi Road",      "AMD", "DEL", 940,  14.0, 0.18, 22000, True,  "road"),
    ("RT-021", "Surat–Mumbai Road",         "STV", "BOM", 280,   5.0, 0.10, 18000, True,  "road"),
    ("RT-022", "Pune–Mumbai Road",          "PNQ", "BOM", 150,   3.0, 0.08, 20000, True,  "road"),
    ("RT-023", "Hyderabad–Mumbai Road",     "HYD", "BOM", 700,  12.0, 0.20, 15000, True,  "road"),
    ("RT-024", "Chennai–Mumbai Sea",        "MAA", "BOM",1350,  60.0, 0.15, 400000, True,  "sea"),
    ("RT-025", "Kochi–Singapore Sea",       "COK", "SIN",2700, 110.0, 0.22, 400000, True,  "sea"),
    ("RT-026", "Delhi–Dubai Air",           "DEL", "DXB",2200,   3.5, 0.12, 9000, True,  "air"),
    ("RT-027", "Bangalore–Singapore Air",   "BLR", "SIN",3300,   5.0, 0.13, 8500, True,  "air"),
    ("RT-028", "Ahmedabad–Dubai via Mumbai","AMD", "DXB",2500,  89.0, 0.22, 25000, True,  "multimodal"),
    ("RT-029", "Kolkata–Singapore Sea",     "CCU", "SIN",2800, 115.0, 0.24, 500000, True,  "sea"),
    ("RT-030", "Mumbai–Frankfurt Air",      "BOM", "FRA",7400,   9.0, 0.16, 12000, True,  "air"),
    # Alternative/contingency routes (higher risk, used when primary is disrupted)
    ("RT-031", "Ahmedabad–Mumbai Alt Road", "AMD", "BOM", 560,  10.5, 0.30, 20000, False, "road"),
    ("RT-032", "Mumbai–Dubai Alt Sea",      "BOM", "DXB",1970,  90.0, 0.40, 400000, False, "sea"),
    ("RT-033", "Chennai–Kochi–Dubai",       "MAA", "DXB",3300, 130.0, 0.35, 350000, False, "sea"),
    ("RT-034", "Delhi–Mumbai Rail",         "DEL", "BOM",1400,  26.0, 0.18, 45000, False, "rail"),
    ("RT-035", "Bangalore–Mumbai Road",     "BLR", "BOM", 980,  16.0, 0.25, 18000, False, "road"),
    ("RT-036", "Kolkata–Delhi Rail",        "CCU", "DEL",1500,  20.0, 0.20, 40000, True,  "rail"),
    ("RT-037", "Hyderabad–Chennai Road",    "HYD", "MAA", 630,  10.0, 0.18, 16000, True,  "road"),
    ("RT-038", "Surat–Delhi Road",          "STV", "DEL",1080,  16.0, 0.22, 18000, True,  "road"),
    ("RT-039", "Pune–Hyderabad Road",       "PNQ", "HYD", 560,   9.0, 0.18, 15000, True,  "road"),
    ("RT-040", "Mumbai–Colombo Sea",        "BOM", "COK",1450,  60.0, 0.28, 300000, False, "sea"),
]

# Cargo types with (type_name, temp_sensitive, min_c, max_c, value_range_usd, weight_range_kg)
CARGO_TYPES = [
    ("Pharmaceutical",     True,  2.0,  8.0,  (50000, 500000), (100, 2000)),
    ("Vaccine",            True,  2.0,  8.0, (200000, 2000000),(50,   500)),
    ("Frozen Seafood",     True, -25.0, -15.0,(5000,   50000),  (500, 8000)),
    ("Fresh Produce",      True,  1.0,  7.0,   (2000,  20000),  (1000, 10000)),
    ("Industrial Chemicals",False, None, None, (10000, 100000), (2000, 20000)),
    ("Electronics",        False, None, None, (100000,1000000), (500,  5000)),
    ("Textiles",           False, None, None,  (5000,  50000),  (2000, 15000)),
    ("Auto Parts",         False, None, None, (20000, 200000),  (3000, 25000)),
    ("Steel",              False, None, None,  (8000,  80000), (10000, 80000)),
    ("Chemicals",          False, None, None, (15000, 150000),  (5000, 30000)),
]

DISRUPTION_DATA = [
    # (code, name, type, severity, region, hours_ago_start, duration_hours, status, desc)
    # ── DEMO disruption ──────────────────────────────────────────────────────
    ("DIS-001", "Mumbai Port Crisis",
     DisruptionType.PORT, 8, "Mumbai Port, India",
     12, 48, DisruptionStatus.ACTIVE,
     "Industrial strike at Mumbai Port affecting container handling. "
     "All outbound container movements suspended. ~300 vessels affected."),
    # ── Active disruptions ────────────────────────────────────────────────────
    ("DIS-002", "Cyclone Tej — Arabian Sea",
     DisruptionType.WEATHER, 7, "Arabian Sea, Gujarat Coast",
     6, 36, DisruptionStatus.ACTIVE,
     "Category 2 cyclone tracking toward Gujarat coast. "
     "Sea freight suspended on Mumbai–Dubai corridor."),
    ("DIS-003", "Suez Canal Congestion",
     DisruptionType.TRANSPORT, 5, "Suez Canal, Egypt",
     72, 120, DisruptionStatus.MONITORING,
     "High vessel traffic causing 2–3 day delays on Europe-bound routes."),
    ("DIS-004", "Chennai Port Equipment Failure",
     DisruptionType.PORT, 4, "Chennai Port, India",
     48, 24, DisruptionStatus.MONITORING,
     "Primary crane failure at terminal 3. Capacity reduced by 40%."),
    ("DIS-005", "Supplier SUP-007 Quality Hold",
     DisruptionType.SUPPLIER, 6, "Surat, India",
     24, 72, DisruptionStatus.ACTIVE,
     "Quality inspection hold on textile batch SUP-007-Q3. "
     "All outbound shipments paused pending audit."),
    # ── Historical disruptions (Disruption DNA reference library) ────────────
    ("DIS-006", "Mumbai Port Strike 2024",
     DisruptionType.PORT, 7, "Mumbai Port, India",
     -(365*24), 96, DisruptionStatus.HISTORICAL,
     "Previous Mumbai Port strike. 4-day full shutdown. "
     "Historical reference for Disruption DNA comparison."),
    ("DIS-007", "Kerala Floods 2024",
     DisruptionType.WEATHER, 9, "Kerala, India",
     -(300*24), 240, DisruptionStatus.HISTORICAL,
     "Severe monsoon flooding disrupting Kochi port and NH-66 road corridor."),
    ("DIS-008", "Cyclone Biparjoy 2023",
     DisruptionType.WEATHER, 8, "Gujarat Coast, India",
     -(450*24), 72, DisruptionStatus.HISTORICAL,
     "Landfall near Jakhau. Road networks in Gujarat disrupted for 3 days."),
    ("DIS-009", "Shanghai Port COVID Lockdown",
     DisruptionType.REGULATORY, 9, "Shanghai, China",
     -(700*24), 720, DisruptionStatus.HISTORICAL,
     "Extended lockdown halted operations at world's busiest port. "
     "Global supply chain impact."),
    ("DIS-010", "Evergreen Suez Blockage",
     DisruptionType.TRANSPORT, 8, "Suez Canal, Egypt",
     -(1200*24), 144, DisruptionStatus.HISTORICAL,
     "MV Ever Given grounding blocked Suez Canal for 6 days. "
     "Global shipping disruption — benchmark event for DNA scoring."),
    ("DIS-011", "Bangalore Flooding 2023",
     DisruptionType.WEATHER, 5, "Bangalore, India",
     -(600*24), 48, DisruptionStatus.HISTORICAL,
     "Urban flooding in Bangalore tech corridors. "
     "Electronics supply chain affected."),
    ("DIS-012", "Red Sea Security Alert",
     DisruptionType.GEOPOLITICAL, 7, "Red Sea, Yemen",
     -(180*24), 2160, DisruptionStatus.MONITORING,
     "Ongoing vessel attacks forcing rerouting around Cape of Good Hope. "
     "+14 days transit time to Europe."),
    ("DIS-013", "Delhi Smog Emergency",
     DisruptionType.REGULATORY, 3, "New Delhi, India",
     -(60*24), 72, DisruptionStatus.HISTORICAL,
     "Odd-even trucking restrictions due to AQI emergency. "
     "Last-mile delays in NCR."),
    ("DIS-014", "Kochi Port Congestion",
     DisruptionType.PORT, 4, "Kochi, India",
     -(30*24), 48, DisruptionStatus.HISTORICAL,
     "Post-holiday backlog at Kochi port. "
     "Average dwell time increased by 2 days."),
    ("DIS-015", "Hyderabad Pharma Audit Hold",
     DisruptionType.SUPPLIER, 5, "Hyderabad, India",
     -(14*24), 96, DisruptionStatus.HISTORICAL,
     "Regulatory inspection hold at pharma manufacturing cluster."),
    ("DIS-016", "Singapore Port Congestion 2024",
     DisruptionType.PORT, 5, "Singapore",
     -(200*24), 168, DisruptionStatus.HISTORICAL,
     "Record vessel waiting times at PSA Singapore. "
     "Transshipment delays of 5–7 days."),
    ("DIS-017", "Rajasthan Border Closure",
     DisruptionType.GEOPOLITICAL, 4, "Rajasthan–Pakistan Border",
     -(120*24), 120, DisruptionStatus.HISTORICAL,
     "Temporary road closure at Munabao border crossing."),
    ("DIS-018", "Typhoon Haikui",
     DisruptionType.WEATHER, 7, "South China Sea",
     -(240*24), 96, DisruptionStatus.HISTORICAL,
     "Typhoon affecting Shanghai and South China shipping lanes."),
    ("DIS-019", "Mumbai–Pune Expressway Closure",
     DisruptionType.TRANSPORT, 3, "Maharashtra, India",
     -(7*24), 18, DisruptionStatus.HISTORICAL,
     "Rockslide near Khopoli causing 18-hour expressway closure."),
    ("DIS-020", "Kolkata Port Workers Strike",
     DisruptionType.PORT, 6, "Kolkata Port, India",
     -(90*24), 72, DisruptionStatus.HISTORICAL,
     "3-day labor action at Kolkata container terminal."),
    ("DIS-021", "EU Pharmaceutical Regulation Change",
     DisruptionType.REGULATORY, 4, "European Union",
     -(45*24), 2160, DisruptionStatus.MONITORING,
     "New documentation requirements for pharma imports to EU. "
     "Ongoing compliance delays."),
    ("DIS-022", "Ahmedabad Road Flooding",
     DisruptionType.WEATHER, 4, "Ahmedabad, India",
     -(20*24), 24, DisruptionStatus.HISTORICAL,
     "Flash flooding on NH-48 disrupting road freight from Ahmedabad."),
    ("DIS-023", "Chennai Auto Strike",
     DisruptionType.SUPPLIER, 5, "Chennai, India",
     -(150*24), 120, DisruptionStatus.HISTORICAL,
     "Labor strike at Chennai auto manufacturing cluster."),
    ("DIS-024", "Pakistan Trade Suspension",
     DisruptionType.GEOPOLITICAL, 6, "India–Pakistan Border",
     -(400*24), 1440, DisruptionStatus.HISTORICAL,
     "Suspension of overland trade routes between India and Pakistan."),
    ("DIS-025", "Mumbai Customs Strike",
     DisruptionType.REGULATORY, 5, "Mumbai, India",
     -(500*24), 48, DisruptionStatus.HISTORICAL,
     "Customs officer walkout causing clearance backlog at JNPT."),
    ("DIS-026", "Bangalore Airport Congestion",
     DisruptionType.TRANSPORT, 3, "Bangalore, India",
     -(25*24), 36, DisruptionStatus.HISTORICAL,
     "Air cargo capacity constraint at Kempegowda International Airport."),
    ("DIS-027", "Kolkata Cyclone Mocha",
     DisruptionType.WEATHER, 6, "Bay of Bengal, Eastern India",
     -(350*24), 72, DisruptionStatus.HISTORICAL,
     "Cyclone making landfall near Myanmar/Bangladesh border. "
     "Eastern India shipping affected."),
    ("DIS-028", "Delhi Airport Strike",
     DisruptionType.TRANSPORT, 4, "New Delhi, India",
     -(60*24), 24, DisruptionStatus.HISTORICAL,
     "Ground handling staff industrial action at Indira Gandhi Airport."),
    ("DIS-029", "Surat Diamond Export Halt",
     DisruptionType.REGULATORY, 3, "Surat, India",
     -(80*24), 48, DisruptionStatus.HISTORICAL,
     "Customs hold on diamond exports pending valuation audit."),
    ("DIS-030", "Kochi Seafood Cold Store Failure",
     DisruptionType.SUPPLIER, 5, "Kochi, India",
     -(15*24), 36, DisruptionStatus.HISTORICAL,
     "Cold storage facility failure at Kochi export cluster. "
     "Temperature-sensitive cargo at risk."),
]


def _ts(hours_offset: float) -> datetime:
    return NOW + timedelta(hours=hours_offset)


def _past(hours_ago: float) -> datetime:
    return NOW - timedelta(hours=abs(hours_ago))


# ─────────────────────────────────────────────────────────────────────────────
def seed_suppliers(session: Session) -> dict[str, int]:
    """Insert suppliers, return {code: id} map."""
    code_to_id: dict[str, int] = {}
    for code, name, country, city, rel, lead, tier in SUPPLIER_DATA:
        sup = Supplier(
            supplier_code=code,
            name=name,
            country=country,
            city=city,
            reliability_score=rel,
            lead_time_days=lead,
            tier=tier,
            contact_email=f"ops@{name.lower().replace(' ', '-')}.com",
            created_at=_past(rng.uniform(100 * 24, 500 * 24)),
        )
        session.add(sup)
        session.flush()
        code_to_id[code] = sup.id
    print(f"  Suppliers: {len(code_to_id)}")
    return code_to_id


def seed_routes(session: Session) -> dict[str, int]:
    """Insert routes, return {code: id} map."""
    code_to_id: dict[str, int] = {}
    for (code, name, orig_hub, dest_hub,
         km, hours, risk, cap, primary, mode) in ROUTE_DATA:
        route = Route(
            route_code=code,
            route_name=name,
            origin=HUBS[orig_hub][0],
            destination=HUBS[dest_hub][0],
            distance_km=float(km),
            duration_hours=float(hours),
            risk_score=float(risk),
            capacity_kg=float(cap),
            is_primary=primary,
            transport_mode=mode,
        )
        session.add(route)
        session.flush()
        code_to_id[code] = route.id
    print(f"  Routes: {len(code_to_id)}")
    return code_to_id


def seed_disruptions(session: Session) -> dict[str, int]:
    """Insert disruptions, return {code: id} map."""
    code_to_id: dict[str, int] = {}
    for (code, name, dtype, severity, region,
         hours_offset, duration_h, status, desc) in DISRUPTION_DATA:
        start = _past(abs(hours_offset)) if hours_offset < 0 else _ts(-abs(hours_offset))
        end = start + timedelta(hours=duration_h)
        dis = Disruption(
            disruption_code=code,
            name=name,
            type=dtype,
            severity=severity,
            affected_region=region,
            start_time=start,
            end_time=end if status != DisruptionStatus.ACTIVE else None,
            status=status,
            description=desc,
        )
        session.add(dis)
        session.flush()
        code_to_id[code] = dis.id
    print(f"  Disruptions: {len(code_to_id)}")
    return code_to_id


def seed_fleet(session: Session) -> dict[str, int]:
    """Insert 50 fleet vehicles, return {code: id} map."""
    vehicle_types = [
        ("Refrigerated Truck", 15000, True),
        ("Flatbed Truck",      25000, False),
        ("Container Truck",    30000, False),
        ("Mini Van",            3000, False),
        ("Refrigerated Van",    5000, True),
    ]

    hub_list = list(HUBS.items())
    code_to_id: dict[str, int] = {}

    # ── Demo vehicle T-101 ────────────────────────────────────────────────────
    amd_lat, amd_lon = HUBS["AMD"][1], HUBS["AMD"][2]
    t101 = FleetVehicle(
        vehicle_code="T-101",
        vehicle_type="Refrigerated Truck",
        capacity_kg=15000.0,
        current_location="Ahmedabad",
        current_lat=amd_lat + rng.uniform(-0.02, 0.02),
        current_lon=amd_lon + rng.uniform(-0.02, 0.02),
        status=VehicleStatus.AVAILABLE,
        available_from=NOW,
        refrigerated=True,
    )
    session.add(t101)
    session.flush()
    code_to_id["T-101"] = t101.id

    for i in range(2, 51):
        code = f"T-{i:03d}"
        vtype, cap, refrig = rng.choice(vehicle_types)
        hub_code, (hub_name, hub_lat, hub_lon) = rng.choice(hub_list)

        # Vary status realistically
        status_weights = [
            (VehicleStatus.AVAILABLE,   0.45),
            (VehicleStatus.IN_TRANSIT,  0.35),
            (VehicleStatus.MAINTENANCE, 0.12),
            (VehicleStatus.RESERVED,    0.08),
        ]
        status = rng.choices(
            [s for s, _ in status_weights],
            weights=[w for _, w in status_weights],
        )[0]

        if status == VehicleStatus.AVAILABLE:
            available_from = NOW - timedelta(hours=rng.uniform(0, 48))
        elif status == VehicleStatus.IN_TRANSIT:
            available_from = NOW + timedelta(hours=rng.uniform(6, 96))
        else:
            available_from = NOW + timedelta(hours=rng.uniform(12, 168))

        v = FleetVehicle(
            vehicle_code=code,
            vehicle_type=vtype,
            capacity_kg=float(cap),
            current_location=hub_name,
            current_lat=hub_lat + rng.uniform(-0.05, 0.05),
            current_lon=hub_lon + rng.uniform(-0.05, 0.05),
            status=status,
            available_from=available_from,
            refrigerated=refrig,
        )
        session.add(v)
        session.flush()
        code_to_id[code] = v.id

    print(f"  Fleet vehicles: {len(code_to_id)}")
    return code_to_id


def seed_shipments(
    session: Session,
    supplier_ids: dict[str, int],
    route_ids: dict[str, int],
) -> tuple[dict[str, int], list[int]]:
    """Insert 500 shipments. Returns ({code: id}, [temp_sensitive_ids])."""
    sup_codes = list(supplier_ids.keys())
    route_codes = list(route_ids.keys())
    code_to_id: dict[str, int] = {}
    temp_sensitive_ids: list[int] = []

    # ── Demo shipment S-1042 ──────────────────────────────────────────────────
    # High-value pharma: Ahmedabad → Dubai via Mumbai  (in transit, delayed)
    dep_time = NOW - timedelta(hours=10)
    eta = NOW + timedelta(hours=70)      # ~3 days total, 10h already elapsed
    s1042 = Shipment(
        shipment_code="S-1042",
        supplier_id=supplier_ids["SUP-001"],  # Ahmedabad Pharma Exports
        origin="Ahmedabad",
        destination="Dubai",
        route_id=route_ids["RT-028"],         # Ahmedabad–Dubai via Mumbai
        cargo_type="Pharmaceutical",
        cargo_value_usd=485000.0,
        weight_kg=1240.0,
        priority=CargoPriority.CRITICAL,
        status=ShipmentStatus.AT_RISK,        # flagged by Mumbai Port Crisis
        departure_time=dep_time,
        eta=eta,
        current_lat=19.0760 + rng.uniform(-0.05, 0.05),  # near Mumbai
        current_lon=72.8777 + rng.uniform(-0.05, 0.05),
        temperature_sensitive=True,
        min_temperature_c=2.0,
        max_temperature_c=8.0,
    )
    session.add(s1042)
    session.flush()
    code_to_id["S-1042"] = s1042.id
    temp_sensitive_ids.append(s1042.id)

    # ── Remaining 499 shipments ───────────────────────────────────────────────
    for i in range(1, 500):
        num = 1000 + i
        if num == 1042:
            num = 1999  # avoid duplicate
        code = f"S-{num}"

        cargo_row = rng.choice(CARGO_TYPES)
        c_type, c_temp, c_min, c_max, val_range, wt_range = cargo_row

        sup_code = rng.choice(sup_codes)
        route_code = rng.choice(route_codes)
        route_entry = next(r for r in ROUTE_DATA if r[0] == route_code)
        orig_hub = route_entry[2]
        dest_hub = route_entry[3]

        priority = rng.choices(
            [CargoPriority.ROUTINE, CargoPriority.STANDARD,
             CargoPriority.HIGH, CargoPriority.CRITICAL],
            weights=[0.25, 0.45, 0.20, 0.10],
        )[0]

        # Departure between 30 days ago and 7 days in future
        dep_offset = rng.uniform(-30 * 24, 7 * 24)
        dep_t = NOW + timedelta(hours=dep_offset)
        route_dur = route_entry[5]
        eta_t = dep_t + timedelta(hours=route_dur * rng.uniform(1.0, 1.4))

        # Status consistent with timing
        if dep_t > NOW:
            status = ShipmentStatus.PLANNED
        elif eta_t < NOW:
            status = rng.choices(
                [ShipmentStatus.DELIVERED, ShipmentStatus.DELAYED],
                weights=[0.88, 0.12],
            )[0]
        else:
            status = rng.choices(
                [ShipmentStatus.IN_TRANSIT, ShipmentStatus.DELAYED, ShipmentStatus.AT_RISK],
                weights=[0.75, 0.15, 0.10],
            )[0]

        # Current position: interpolate between origin and destination
        origin_hub_data = HUBS.get(orig_hub)
        dest_hub_data = HUBS.get(dest_hub)
        if origin_hub_data and dest_hub_data and status == ShipmentStatus.IN_TRANSIT:
            elapsed = (NOW - dep_t).total_seconds() / 3600
            frac = min(max(elapsed / route_dur, 0.0), 1.0)
            cur_lat = origin_hub_data[1] + frac * (dest_hub_data[1] - origin_hub_data[1])
            cur_lon = origin_hub_data[2] + frac * (dest_hub_data[2] - origin_hub_data[2])
            cur_lat += rng.uniform(-0.2, 0.2)
            cur_lon += rng.uniform(-0.2, 0.2)
        else:
            cur_lat = origin_hub_data[1] + rng.uniform(-0.1, 0.1) if origin_hub_data else None
            cur_lon = origin_hub_data[2] + rng.uniform(-0.1, 0.1) if origin_hub_data else None

        s = Shipment(
            shipment_code=code,
            supplier_id=supplier_ids[sup_code],
            origin=HUBS.get(orig_hub, (orig_hub,))[0],
            destination=HUBS.get(dest_hub, (dest_hub,))[0],
            route_id=route_ids[route_code],
            cargo_type=c_type,
            cargo_value_usd=float(rng.uniform(*val_range)),
            weight_kg=float(rng.uniform(*wt_range)),
            priority=priority,
            status=status,
            departure_time=dep_t,
            eta=eta_t,
            current_lat=cur_lat,
            current_lon=cur_lon,
            temperature_sensitive=c_temp,
            min_temperature_c=float(c_min) if c_min is not None else None,
            max_temperature_c=float(c_max) if c_max is not None else None,
        )
        session.add(s)
        session.flush()
        code_to_id[code] = s.id
        if c_temp:
            temp_sensitive_ids.append(s.id)

    print(f"  Shipments: {len(code_to_id)} (temp-sensitive: {len(temp_sensitive_ids)})")
    return code_to_id, temp_sensitive_ids


def seed_shipment_disruptions(
    session: Session,
    shipment_ids: dict[str, int],
    disruption_ids: dict[str, int],
) -> None:
    """Link shipments to disruptions with realistic impact scores."""
    links_created = 0

    # S-1042 is directly affected by DIS-001 (Mumbai Port Crisis)
    sd = ShipmentDisruption(
        shipment_id=shipment_ids["S-1042"],
        disruption_id=disruption_ids["DIS-001"],
        impact_score=0.85,
        delay_hours=48.0,
    )
    session.add(sd)
    links_created += 1

    # S-1042 also affected by DIS-002 (Cyclone — Arabian Sea route)
    sd2 = ShipmentDisruption(
        shipment_id=shipment_ids["S-1042"],
        disruption_id=disruption_ids["DIS-002"],
        impact_score=0.60,
        delay_hours=24.0,
    )
    session.add(sd2)
    links_created += 1

    # Randomly link other active disruptions to shipments
    # Active disruptions: DIS-001..005
    active_dis_codes = ["DIS-001", "DIS-002", "DIS-003", "DIS-004", "DIS-005"]
    all_ship_codes = [c for c in shipment_ids if c != "S-1042"]

    for dis_code in active_dis_codes:
        # Each active disruption affects 5–20% of shipments
        n_affected = int(len(all_ship_codes) * rng.uniform(0.05, 0.20))
        affected = rng.sample(all_ship_codes, n_affected)
        for s_code in affected:
            impact = round(rng.uniform(0.1, 0.9), 2)
            delay = round(rng.uniform(4, 72), 1)
            session.add(ShipmentDisruption(
                shipment_id=shipment_ids[s_code],
                disruption_id=disruption_ids[dis_code],
                impact_score=impact,
                delay_hours=delay,
            ))
            links_created += 1

    print(f"  Shipment-disruption links: {links_created}")


def seed_cold_chain_readings(
    session: Session,
    shipment_ids: dict[str, int],
    temp_sensitive_ids: list[int],
) -> None:
    """Generate cold-chain telemetry. Targets ~100k+ readings total."""
    total_readings = 0
    BATCH_SIZE = 5000

    s1042_id = shipment_ids["S-1042"]

    def flush_if(batch: list) -> list:
        if len(batch) >= BATCH_SIZE:
            session.bulk_save_objects(batch)
            session.flush()
            return []
        return batch

    batch: list[ColdChainReading] = []

    # ── S-1042: detailed readings every 5 minutes for 10 hours (120 readings)
    # with a realistic temperature excursion between hours 6–8
    s1042_dep = NOW - timedelta(hours=10)
    SENSOR_ID_MAIN = "SN-1042-A"
    SENSOR_ID_BACKUP = "SN-1042-B"
    normal_temp = 4.5   # target centre (2–8°C range)
    excursion_peak = 9.8  # just above 8.0 limit — not absurdly large

    for minute in range(0, 600, 5):   # every 5 minutes for 10 hours = 120 readings
        ts = s1042_dep + timedelta(minutes=minute)
        hour = minute / 60.0

        # Build realistic temperature profile:
        #   hours 0–6   : stable 4.0–5.5 °C (normal)
        #   hours 6–8   : rises to 9.8°C (brief excursion — door opened at stop)
        #   hours 8–10  : recovers back to 4.5–5.5°C (reefer restores)
        if hour < 6.0:
            base = 4.5 + rng.uniform(-0.4, 0.6)
            noise = rng.gauss(0, 0.15)
            temp = round(base + noise, 2)
            is_breach = False
        elif hour < 8.0:
            # Gradual rise then fall: peak at hour 7
            t_frac = (hour - 6.0) / 2.0  # 0→1→0 shape
            excursion = normal_temp + (excursion_peak - normal_temp) * (
                4 * t_frac * (1 - t_frac)  # parabolic peak at t_frac=0.5
            )
            noise = rng.gauss(0, 0.2)
            temp = round(excursion + noise, 2)
            is_breach = temp > 8.0
        else:
            # Recovery
            recovery_frac = (hour - 8.0) / 2.0
            temp = round((excursion_peak * (1 - recovery_frac) + 4.5 * recovery_frac)
                         + rng.gauss(0, 0.15), 2)
            is_breach = temp > 8.0

        humidity = round(rng.uniform(55.0, 70.0), 1)

        for sensor in (SENSOR_ID_MAIN, SENSOR_ID_BACKUP):
            # Backup sensor has slightly different readings
            t_adj = temp + rng.uniform(-0.3, 0.3) if sensor == SENSOR_ID_BACKUP else temp
            batch.append(ColdChainReading(
                shipment_id=s1042_id,
                sensor_id=sensor,
                temperature_c=round(t_adj, 2),
                humidity_pct=humidity,
                recorded_at=ts,
                is_breach=round(t_adj, 2) > 8.0,
            ))
            total_readings += 1
        batch = flush_if(batch)

    # ── Other temp-sensitive shipments: readings every 15 minutes per shipment
    other_ts_ids = [sid for sid in temp_sensitive_ids if sid != s1042_id]

    # All temp-sensitive shipments get readings for their full journey
    # (departure → eta), using the full route window regardless of "now".
    # Interval = 10 minutes per shipment to hit 100k+ total.
    for ship_id in other_ts_ids:
        ship = session.get(Shipment, ship_id)
        if ship is None:
            continue

        ship_start = ship.departure_time
        ship_end = ship.eta
        if ship_start >= ship_end:
            ship_end = ship_start + timedelta(hours=6)

        duration_minutes = int((ship_end - ship_start).total_seconds() / 60)
        # Every 10 minutes guarantees at least 6 readings for a 1-hour shipment
        interval = 10
        n_readings = max(duration_minutes // interval, 6)

        c_min = ship.min_temperature_c if ship.min_temperature_c is not None else -25.0
        c_max = ship.max_temperature_c if ship.max_temperature_c is not None else -15.0
        target = (c_min + c_max) / 2.0
        spread = max((c_max - c_min) / 4.0, 0.5)

        # Two sensors per shipment — doubles reading count
        for sensor_suffix in ("A", "B"):
            sensor_id = f"SN-{ship_id:04d}-{sensor_suffix}"
            for j in range(n_readings):
                ts = ship_start + timedelta(minutes=j * interval)
                base_temp = rng.gauss(target, spread * 0.3)
                # Sensor B has ±0.3°C offset vs sensor A
                t_adj = base_temp + (rng.uniform(-0.3, 0.3) if sensor_suffix == "B" else 0.0)
                temp = round(t_adj, 2)
                is_breach = temp < c_min or temp > c_max
                humidity = round(rng.uniform(45.0, 80.0), 1)
                batch.append(ColdChainReading(
                    shipment_id=ship_id,
                    sensor_id=sensor_id,
                    temperature_c=temp,
                    humidity_pct=humidity,
                    recorded_at=ts,
                    is_breach=is_breach,
                ))
                total_readings += 1
            batch = flush_if(batch)

    # Flush any remaining
    if batch:
        session.bulk_save_objects(batch)
        session.flush()

    print(f"  Cold-chain readings: {total_readings}")


def seed_resilience_wallets(
    session: Session,
    supplier_ids: dict[str, int],
    route_ids: dict[str, int],
) -> None:
    """Create resilience wallet placeholders for all suppliers and key routes."""
    count = 0
    # Per-supplier wallets (4 dimensions each)
    for sup_code, sup_id in supplier_ids.items():
        sup_entry = next(s for s in SUPPLIER_DATA if s[0] == sup_code)
        rel = sup_entry[4]
        lead = sup_entry[5]

        dimension_defaults = {
            WalletDimension.TIME:        (lead * 24 * rel,        lead * 24),
            WalletDimension.COST:        (100000 * rel,           100000),
            WalletDimension.TEMPERATURE: (500 * rel,              500),
            WalletDimension.CAPACITY:    (50000 * rel,            50000),
        }
        for dim, (balance, max_bal) in dimension_defaults.items():
            w = ResilienceWallet(
                owner_type="supplier",
                owner_id=sup_id,
                dimension=dim,
                balance=round(balance, 2),
                max_balance=round(max_bal, 2),
            )
            session.add(w)
            session.flush()
            # Seed transaction
            session.add(ResilienceTransaction(
                wallet_id=w.id,
                dimension=dim,
                amount=round(balance, 2),
                reason="Initial wallet balance from seed",
                reference_id=sup_code,
            ))
            count += 1

    # System-level wallet
    for dim, (bal, max_bal) in {
        WalletDimension.TIME:        (4800.0, 5000.0),
        WalletDimension.COST:        (5000000.0, 6000000.0),
        WalletDimension.TEMPERATURE: (10000.0, 12000.0),
        WalletDimension.CAPACITY:    (2000000.0, 2500000.0),
    }.items():
        w = ResilienceWallet(
            owner_type="system",
            owner_id=0,
            dimension=dim,
            balance=bal,
            max_balance=max_bal,
        )
        session.add(w)
        session.flush()
        session.add(ResilienceTransaction(
            wallet_id=w.id,
            dimension=dim,
            amount=bal,
            reason="System wallet initialised from seed",
            reference_id="SYSTEM",
        ))
        count += 1

    print(f"  Resilience wallets: {count} (+ {count} initial transactions)")


def seed_demo_resilience_impact(
    session: Session,
    shipment_ids: dict[str, int],
    disruption_ids: dict[str, int],
) -> None:
    """Apply the recorded Mumbai event to the S-1042 wallet once.

    This reuses the production disruption-impact service so the seeded demo
    transaction ledger, wallet balances, and RRI tell the same deterministic
    story as the API. Other linked shipments remain available as raw impact
    records and are not mass-applied to avoid obscuring the demo scenario.
    """
    shipment = session.get(Shipment, shipment_ids["S-1042"])
    link = session.get(
        ShipmentDisruption,
        (shipment_ids["S-1042"], disruption_ids["DIS-001"]),
    )
    if shipment is None or link is None:
        raise RuntimeError("S-1042 / DIS-001 demo relationship is missing")
    initialise_shipment_wallets(session, shipment)
    apply_disruption_to_shipment(session, shipment, link, "DIS-001")
    print("  Demo resilience impact: DIS-001 applied to S-1042 wallet")


def seed_audit_log(
    session: Session,
    shipment_ids: dict[str, int],
) -> None:
    """Insert a few seed-time audit entries as a baseline."""
    entries = [
        ("seed", "schema_created", "system",     "0",     None, {"version": "1.0.0"}, "seed"),
        ("seed", "data_seeded",    "system",     "0",     None, {"shipments": len(shipment_ids)}, "seed"),
        ("seed", "created",        "shipment",  "S-1042", None, {"status": "at_risk", "cargo": "Pharmaceutical"}, "seed"),
    ]
    for actor, action, etype, eid, before, after, source in entries:
        session.add(AuditLog(
            actor=actor,
            action=action,
            entity_type=etype,
            entity_id=eid,
            before_state=before,
            after_state=after,
            source=source,
        ))
    print(f"  Audit log entries: {len(entries)}")


# ─────────────────────────────────────────────────────────────────────────────
def reset_all(engine) -> None:
    """Drop all seed data in dependency order before re-seeding."""
    tables_in_order = [
        "resilience_transactions", "resilience_wallets",
        "cold_chain_readings", "shipment_disruptions",
        "rri_snapshots", "recovery_plans", "simulation_runs",
        "approvals", "audit_log",
        "shipments", "disruptions", "fleet_vehicles",
        "routes", "suppliers",
    ]
    with engine.begin() as conn:
        for table in tables_in_order:
            # RESTART IDENTITY requires ownership of every attached sequence,
            # which is not available to many least-privilege application roles.
            # Seed records are addressed by stable business codes, not sequence IDs.
            conn.execute(text(f"TRUNCATE TABLE {table} CASCADE"))
    print("  Reset: all seed tables truncated.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed the SupplyShield database")
    parser.add_argument("--reset", action="store_true",
                        help="Truncate all tables before seeding (idempotent)")
    args = parser.parse_args()

    url = os.environ.get("DATABASE_SYNC_URL", "")
    if not url:
        try:
            load_dotenv()
            url = os.environ.get("DATABASE_SYNC_URL", "")
        except Exception:
            pass
    if not url:
        print("ERROR: DATABASE_SYNC_URL not set.")
        sys.exit(1)

    engine = create_engine(url, echo=False)

    if args.reset:
        print("Resetting all seed tables...")
        reset_all(engine)

    print("Seeding SupplyShield database...")
    with Session(engine) as session:
        supplier_ids = seed_suppliers(session)
        route_ids = seed_routes(session)
        disruption_ids = seed_disruptions(session)
        fleet_ids = seed_fleet(session)
        shipment_ids, temp_sensitive_ids = seed_shipments(
            session, supplier_ids, route_ids
        )
        seed_shipment_disruptions(session, shipment_ids, disruption_ids)
        seed_cold_chain_readings(session, shipment_ids, temp_sensitive_ids)
        seed_resilience_wallets(session, supplier_ids, route_ids)
        seed_demo_resilience_impact(session, shipment_ids, disruption_ids)
        seed_audit_log(session, shipment_ids)
        session.commit()

    print(f"\nSeed complete. Fleet vehicles seeded: {len(fleet_ids)}")


if __name__ == "__main__":
    main()
