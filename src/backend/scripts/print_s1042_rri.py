"""Print S-1042 baseline and post-disruption RRI numbers."""
import os, sys
sys.path.insert(0, '.')
from dotenv import load_dotenv; load_dotenv()
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.models.shipment import Shipment
from app.models.route import Route
from app.services.wallet_service import (
    calculate_time_budget, calculate_cost_budget,
    calculate_temperature_budget, calculate_capacity_budget,
    DimensionState, WalletState,
)
from app.models.resilience import WalletDimension
from app.services.rri_calculator import calculate_rri
from app.services.resilience_config import DEFAULT_CONFIG

url = os.environ['DATABASE_SYNC_URL']
engine = create_engine(url)
with Session(engine) as s:
    ship = s.query(Shipment).filter_by(shipment_code='S-1042').first()
    route = s.get(Route, ship.route_id) if ship.route_id else None
    ship.route = route
    rd = route.duration_hours if route else 89.0
    rr = route.risk_score if route else 0.22
    rname = route.route_name if route else "unknown"

    tb   = calculate_time_budget(ship, rd, DEFAULT_CONFIG)
    cb   = calculate_cost_budget(ship, rr, DEFAULT_CONFIG)
    tmpb = calculate_temperature_budget(ship, rd, DEFAULT_CONFIG)
    capb = calculate_capacity_budget(ship, rr, DEFAULT_CONFIG)

    print(f"S-1042: {ship.origin} -> {ship.destination}  ({rname})")
    print(f"  Route: {rd}h duration, risk={rr}")
    print(f"  Priority: {ship.priority.value}  Cargo: ${float(ship.cargo_value_usd):,.0f}  Weight: {ship.weight_kg}kg")
    print(f"  TIME budget:      {tb:.2f} hours")
    print(f"  COST budget:      ${cb:,.2f}")
    print(f"  TEMP budget:      {tmpb:.2f} degC*hours")
    print(f"  CAPACITY budget:  {capb:.2f} kg")

    ws = WalletState(
        shipment_id=ship.id, shipment_code='S-1042',
        time=DimensionState(WalletDimension.TIME, tb, tb, 'hours'),
        cost=DimensionState(WalletDimension.COST, cb, cb, 'USD'),
        temperature=DimensionState(WalletDimension.TEMPERATURE, tmpb, tmpb, 'degC_hours'),
        capacity=DimensionState(WalletDimension.CAPACITY, capb, capb, 'kg'),
    )
    exp_base = calculate_rri(ws, ship.priority, DEFAULT_CONFIG)
    print(f"\nBASELINE RRI = {exp_base.rri}  status={exp_base.status.value}")
    print(f"  Dim scores: TIME={exp_base.dimensions['time']:.1f}  COST={exp_base.dimensions['cost']:.1f}  TEMP={exp_base.dimensions['temperature']:.1f}  CAP={exp_base.dimensions['capacity']:.1f}")
    print(f"  Criticality adjustment: {exp_base.criticality_adjustment:.2f}")

    a = DEFAULT_CONFIG.disruption
    impact, delay = 0.85, 48.0
    tc   = delay * impact * a.time_multiplier
    cc   = float(ship.cargo_value_usd) * impact * a.cost_fraction
    tmpc = 7.833 * a.temp_multiplier
    capc = ship.weight_kg * impact * a.capacity_fraction

    print(f"\nDIS-001 Mumbai Port Crisis (impact={impact}, delay={delay}h):")
    print(f"  TIME consumed:  {tc:.2f}h")
    print(f"  COST consumed:  ${cc:,.2f}")
    print(f"  TEMP consumed:  {tmpc:.2f} degC*h")
    print(f"  CAP consumed:   {capc:.2f} kg")

    ws_after = WalletState(
        shipment_id=ship.id, shipment_code='S-1042',
        time=DimensionState(WalletDimension.TIME, tb, max(tb - tc, 0), 'hours'),
        cost=DimensionState(WalletDimension.COST, cb, max(cb - cc, 0), 'USD'),
        temperature=DimensionState(WalletDimension.TEMPERATURE, tmpb, max(tmpb - tmpc, 0), 'degC_hours'),
        capacity=DimensionState(WalletDimension.CAPACITY, capb, max(capb - capc, 0), 'kg'),
    )
    exp_after = calculate_rri(ws_after, ship.priority, DEFAULT_CONFIG)
    print(f"\nPOST-DISRUPTION RRI = {exp_after.rri}  status={exp_after.status.value}")
    print(f"  Dim scores: TIME={exp_after.dimensions['time']:.1f}  COST={exp_after.dimensions['cost']:.1f}  TEMP={exp_after.dimensions['temperature']:.1f}  CAP={exp_after.dimensions['capacity']:.1f}")
    print(f"  Resilience bankrupt: {exp_after.is_resilience_bankrupt}")
    print(f"  RRI drop: {exp_base.rri - exp_after.rri:.2f} points")
