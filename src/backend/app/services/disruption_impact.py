"""Disruption Impact Service.

Applies a disruption event's operational consequences to a shipment's
resilience wallet in a deterministic, documented way.

All conversion assumptions are in resilience_config.DisruptionConsumptionAssumptions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

from app.models.cold_chain import ColdChainReading
from app.models.disruption import ShipmentDisruption
from app.models.resilience import ResilienceWallet, WalletDimension
from app.models.shipment import Shipment
from app.services.resilience_config import ResilienceConfig, DEFAULT_CONFIG
from app.services.wallet_service import consume_resilience, get_wallet_state


@dataclass
class DisruptionConsumptionResult:
    """What was consumed from each dimension and why."""
    shipment_id: int
    disruption_code: str
    time_consumed: float       # hours
    cost_consumed: float       # USD
    temperature_consumed: float  # °C·hours
    capacity_consumed: float   # kg
    breach_degree_hours: float  # measured from DB readings
    transactions_created: int


def _breach_degree_hours(
    session: "Session",
    shipment: Shipment,
) -> float:
    """
    Calculate the total temperature breach exposure for a shipment
    from its cold_chain_readings where is_breach = True.

    Each breach reading represents a 5–15 minute interval.
    We approximate: each breach reading = interval_minutes / 60 hours
    of temperature excursion at the measured deviation above/below spec.

    Estimated interval: 10 minutes per reading (conservative).
    """
    if not shipment.temperature_sensitive:
        return 0.0

    breach_readings = (
        session.query(ColdChainReading)
        .filter_by(shipment_id=shipment.id, is_breach=True)
        .all()
    )
    if not breach_readings:
        return 0.0

    t_min = shipment.min_temperature_c or 2.0
    t_max = shipment.max_temperature_c or 8.0
    interval_hours = 10.0 / 60.0  # 10-minute reading interval

    total: float = 0.0
    for r in breach_readings:
        if r.temperature_c > t_max:
            deviation = r.temperature_c - t_max
        else:
            deviation = t_min - r.temperature_c
        total += deviation * interval_hours

    return round(total, 4)


def apply_disruption_to_shipment(
    session: "Session",
    shipment: Shipment,
    link: ShipmentDisruption,
    disruption_code: str,
    cfg: ResilienceConfig = DEFAULT_CONFIG,
) -> DisruptionConsumptionResult:
    """
    Apply a disruption's impact to a shipment's resilience wallet.

    Consumption formulas (from DisruptionConsumptionAssumptions):

    TIME:
        consumed = link.delay_hours × link.impact_score × time_multiplier

    COST:
        consumed = cargo_value_usd × link.impact_score × cost_fraction

    TEMPERATURE (only for cold cargo):
        consumed = breach_degree_hours × temp_multiplier

    CAPACITY:
        consumed = weight_kg × link.impact_score × capacity_fraction

    Each dimension is consumed only if the wallet budget > 0.
    A ResilienceTransaction is created for every debit.
    """
    a = cfg.disruption
    ref = disruption_code
    wallets = {
        w.dimension: w
        for w in session.query(ResilienceWallet).filter_by(
            owner_type="shipment", owner_id=shipment.id
        ).all()
    }

    # Ensure wallets exist (initialise if missing)
    if not wallets:
        from app.services.wallet_service import initialise_shipment_wallets
        raw = initialise_shipment_wallets(session, shipment, cfg)
        wallets = {dim: w for dim, w in raw.items()}

    cargo_value = float(shipment.cargo_value_usd)
    impact = link.impact_score
    delay = link.delay_hours
    tx_count = 0

    # ── TIME ──────────────────────────────────────────────────────────────────
    time_consumed = round(delay * impact * a.time_multiplier, 4)
    if time_consumed > 0 and WalletDimension.TIME in wallets:
        consume_resilience(
            session, wallets[WalletDimension.TIME],
            time_consumed,
            reason=f"Delay from {disruption_code}: {delay}h × impact {impact:.2f}",
            reference_id=ref,
        )
        tx_count += 1

    # ── COST ──────────────────────────────────────────────────────────────────
    cost_consumed = round(cargo_value * impact * a.cost_fraction, 4)
    if cost_consumed > 0 and WalletDimension.COST in wallets:
        consume_resilience(
            session, wallets[WalletDimension.COST],
            cost_consumed,
            reason=f"Recovery cost from {disruption_code}: "
                   f"cargo_value {cargo_value:.0f} × impact {impact:.2f} × {a.cost_fraction}",
            reference_id=ref,
        )
        tx_count += 1

    # ── TEMPERATURE ───────────────────────────────────────────────────────────
    breach_dh = _breach_degree_hours(session, shipment)
    temp_consumed = round(breach_dh * a.temp_multiplier, 4)
    if temp_consumed > 0 and WalletDimension.TEMPERATURE in wallets:
        consume_resilience(
            session, wallets[WalletDimension.TEMPERATURE],
            temp_consumed,
            reason=f"Temperature excursion during {disruption_code}: "
                   f"{breach_dh:.2f} °C·h measured from sensor breaches",
            reference_id=ref,
        )
        tx_count += 1

    # ── CAPACITY ──────────────────────────────────────────────────────────────
    capacity_consumed = round(shipment.weight_kg * impact * a.capacity_fraction, 4)
    if capacity_consumed > 0 and WalletDimension.CAPACITY in wallets:
        consume_resilience(
            session, wallets[WalletDimension.CAPACITY],
            capacity_consumed,
            reason=f"Capacity allocation from {disruption_code}: "
                   f"weight {shipment.weight_kg:.0f} kg × impact {impact:.2f}",
            reference_id=ref,
        )
        tx_count += 1

    return DisruptionConsumptionResult(
        shipment_id=shipment.id,
        disruption_code=disruption_code,
        time_consumed=time_consumed,
        cost_consumed=cost_consumed,
        temperature_consumed=temp_consumed,
        capacity_consumed=capacity_consumed,
        breach_degree_hours=breach_dh,
        transactions_created=tx_count,
    )
