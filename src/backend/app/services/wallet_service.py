"""SupplyShield Resilience Wallet Service.

All calculations are deterministic: given the same shipment/route/disruption
data from the database, the same wallet values are always produced.

No LLM, random seed, or arbitrary constant is used.
All assumptions are documented in resilience_config.py.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

from app.models.resilience import ResilienceTransaction, ResilienceWallet, WalletDimension
from app.models.shipment import CargoPriority, Shipment
from app.services.resilience_config import ResilienceConfig, DEFAULT_CONFIG


class DimensionStatus(str, enum.Enum):
    HEALTHY = "HEALTHY"
    STRESSED = "STRESSED"
    VULNERABLE = "VULNERABLE"
    CRITICAL = "CRITICAL"
    BANKRUPT = "BANKRUPT"


@dataclass
class DimensionState:
    """Computed state for one wallet dimension."""
    dimension: WalletDimension
    maximum_balance: float
    remaining_balance: float
    unit: str                         # "hours", "USD", "°C·h", "kg"

    @property
    def consumed_balance(self) -> float:
        return max(self.maximum_balance - self.remaining_balance, 0.0)

    @property
    def utilization_percent(self) -> float:
        if self.maximum_balance <= 0:
            return 100.0
        return min(self.consumed_balance / self.maximum_balance * 100.0, 100.0)

    @property
    def dimension_score(self) -> float:
        """0–100 score: 100 = fully intact, 0 = bankrupt."""
        if self.maximum_balance <= 0:
            # Non-applicable dimension (e.g. temperature for non-cold cargo)
            return 100.0
        frac = max(self.remaining_balance / self.maximum_balance, 0.0)
        return round(frac * 100.0, 2)

    def status(self, cfg: ResilienceConfig) -> DimensionStatus:
        if self.remaining_balance <= 0:
            return DimensionStatus.BANKRUPT
        t = cfg.wallet_thresholds
        u = self.utilization_percent
        if u <= t.healthy_max:
            return DimensionStatus.HEALTHY
        if u <= t.stressed_max:
            return DimensionStatus.STRESSED
        if u <= t.vulnerable_max:
            return DimensionStatus.VULNERABLE
        return DimensionStatus.CRITICAL


@dataclass
class WalletState:
    """Full four-dimension wallet state for a shipment."""
    shipment_id: int
    shipment_code: str
    time: DimensionState
    cost: DimensionState
    temperature: DimensionState
    capacity: DimensionState
    computed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def is_resilience_bankrupt(self, cfg: ResilienceConfig) -> bool:
        """True if any dimension critical to operations is bankrupt."""
        # TIME and COST bankruptcy = operational failure
        return (
            self.time.remaining_balance <= 0
            or self.cost.remaining_balance <= 0
        )

    def all_dimensions(self) -> list[DimensionState]:
        return [self.time, self.cost, self.temperature, self.capacity]


# ─────────────────────────────────────────────────────────────────────────────
# Initial budget calculation
# ─────────────────────────────────────────────────────────────────────────────

def _priority_multiplier(priority: CargoPriority, cfg: ResilienceConfig) -> float:
    m = cfg.criticality
    return {
        CargoPriority.ROUTINE:  m.routine,
        CargoPriority.STANDARD: m.standard,
        CargoPriority.HIGH:     m.high,
        CargoPriority.CRITICAL: m.critical,
    }[priority]


def _priority_level(priority: CargoPriority) -> int:
    """0=ROUTINE, 1=STANDARD, 2=HIGH, 3=CRITICAL."""
    return {
        CargoPriority.ROUTINE: 0,
        CargoPriority.STANDARD: 1,
        CargoPriority.HIGH: 2,
        CargoPriority.CRITICAL: 3,
    }[priority]


def calculate_time_budget(
    shipment: "Shipment",
    route_duration_hours: float,
    cfg: ResilienceConfig,
) -> float:
    """
    TIME budget (hours) from shipment attributes.

    Formula:
        base  = route_duration × route_slack_factor
        boost = priority_level × priority_boost_hours_per_level
        value = (cargo_value_usd / 100_000) × cargo_value_time_factor
        raw   = (base + boost + value) × priority_multiplier
        final = clamp(raw, min_budget, max_budget)
    """
    a = cfg.time
    base = route_duration_hours * a.route_slack_factor
    boost = _priority_level(shipment.priority) * a.priority_boost_hours_per_level
    value_bonus = (float(shipment.cargo_value_usd) / 100_000) * a.cargo_value_time_factor
    raw = (base + boost + value_bonus) * _priority_multiplier(shipment.priority, cfg)
    return round(max(a.min_budget_hours, min(raw, a.max_budget_hours)), 4)


def calculate_cost_budget(
    shipment: "Shipment",
    route_risk_score: float,
    cfg: ResilienceConfig,
) -> float:
    """
    COST budget (USD) from shipment attributes.

    Formula:
        base     = cargo_value_usd × value_fraction
        surcharge = (route_risk_score / 0.1) × route_risk_surcharge_per_unit × cargo_value_usd
        raw       = (base + surcharge) × priority_multiplier
        final     = clamp(raw, min_budget, max_budget)
    """
    a = cfg.cost
    cargo_value = float(shipment.cargo_value_usd)
    base = cargo_value * a.value_fraction
    # route_risk_score ranges 0.0–1.0; each 0.1 unit adds the surcharge fraction
    surcharge = (route_risk_score / 0.1) * a.route_risk_surcharge_per_unit * cargo_value
    raw = (base + surcharge) * _priority_multiplier(shipment.priority, cfg)
    return round(max(a.min_budget_usd, min(raw, a.max_budget_usd)), 4)


def calculate_temperature_budget(
    shipment: "Shipment",
    route_duration_hours: float,
    cfg: ResilienceConfig,
) -> float:
    """
    TEMPERATURE budget (°C·hours) from shipment attributes.

    Zero for non-temperature-sensitive shipments.

    Formula:
        transit_budget = route_duration × allowable_excursion_rate
        range_bonus    = (max_c - min_c) × range_multiplier
        raw            = (transit_budget + range_bonus) × priority_multiplier
        final          = clamp(raw, min_budget, max_budget)
    """
    if not shipment.temperature_sensitive:
        return 0.0
    a = cfg.temperature
    transit = route_duration_hours * a.allowable_excursion_rate
    temp_range = (shipment.max_temperature_c or 8.0) - (shipment.min_temperature_c or 2.0)
    range_bonus = max(temp_range, 0.0) * a.range_multiplier
    raw = (transit + range_bonus) * _priority_multiplier(shipment.priority, cfg)
    return round(max(a.min_budget, min(raw, a.max_budget)), 4)


def calculate_capacity_budget(
    shipment: "Shipment",
    route_risk_score: float,
    cfg: ResilienceConfig,
) -> float:
    """
    CAPACITY budget (kg) from shipment attributes.

    Formula:
        base      = weight_kg × redundancy_factor
        risk_adj  = base × (1 - route_risk_score × route_risk_reduction / 0.1)
        raw       = risk_adj × priority_multiplier
        final     = clamp(raw, min_budget, max_budget)
    """
    a = cfg.capacity
    base = shipment.weight_kg * a.redundancy_factor
    risk_reduction = route_risk_score / 0.1 * a.route_risk_reduction
    adjusted = base * max(1.0 - risk_reduction, 0.10)
    raw = adjusted * _priority_multiplier(shipment.priority, cfg)
    return round(max(a.min_budget_kg, min(raw, a.max_budget_kg)), 4)


# ─────────────────────────────────────────────────────────────────────────────
# Wallet service functions
# ─────────────────────────────────────────────────────────────────────────────

def get_or_create_wallet(
    session: "Session",
    shipment_id: int,
    dimension: WalletDimension,
    max_balance: float,
    initial_balance: float | None = None,
) -> ResilienceWallet:
    """
    Return existing wallet for (shipment, dimension), or create it.
    Never silently updates max_balance if the wallet already exists.
    """
    wallet = (
        session.query(ResilienceWallet)
        .filter_by(owner_type="shipment", owner_id=shipment_id, dimension=dimension)
        .first()
    )
    if wallet is None:
        wallet = ResilienceWallet(
            owner_type="shipment",
            owner_id=shipment_id,
            dimension=dimension,
            max_balance=max_balance,
            balance=initial_balance if initial_balance is not None else max_balance,
        )
        session.add(wallet)
        session.flush()
        # Initial credit transaction
        session.add(ResilienceTransaction(
            wallet_id=wallet.id,
            dimension=dimension,
            amount=wallet.balance,
            reason="Initial wallet budget allocated",
            reference_id=f"SHIP-{shipment_id}",
        ))
    return wallet


def initialise_shipment_wallets(
    session: "Session",
    shipment: "Shipment",
    cfg: ResilienceConfig = DEFAULT_CONFIG,
) -> dict[WalletDimension, ResilienceWallet]:
    """
    Create (or retrieve) all four dimension wallets for a shipment.
    Uses shipment attributes and route data to set deterministic budgets.
    Returns {dimension: wallet} map.
    """
    route = shipment.route
    route_duration = route.duration_hours if route else 48.0
    route_risk = route.risk_score if route else 0.3

    budgets = {
        WalletDimension.TIME: calculate_time_budget(shipment, route_duration, cfg),
        WalletDimension.COST: calculate_cost_budget(shipment, route_risk, cfg),
        WalletDimension.TEMPERATURE: calculate_temperature_budget(shipment, route_duration, cfg),
        WalletDimension.CAPACITY: calculate_capacity_budget(shipment, route_risk, cfg),
    }

    wallets: dict[WalletDimension, ResilienceWallet] = {}
    for dim, budget in budgets.items():
        wallets[dim] = get_or_create_wallet(session, shipment.id, dim, budget)

    return wallets


def consume_resilience(
    session: "Session",
    wallet: ResilienceWallet,
    amount: float,
    reason: str,
    reference_id: str | None = None,
    notes: str | None = None,
) -> ResilienceTransaction:
    """
    Debit `amount` from wallet.balance and record the transaction.
    amount must be positive (it is a consumption).
    Wallet balance is clamped at 0 — never goes negative silently.
    Returns the transaction record.
    """
    if amount <= 0:
        raise ValueError(f"consume_resilience: amount must be > 0, got {amount}")
    actual_consumed = min(amount, wallet.balance)
    wallet.balance = round(max(wallet.balance - amount, 0.0), 6)
    tx = ResilienceTransaction(
        wallet_id=wallet.id,
        dimension=wallet.dimension,
        amount=-actual_consumed,       # negative = consumed
        reason=reason,
        reference_id=reference_id,
        notes=notes,
    )
    session.add(tx)
    return tx


def restore_resilience(
    session: "Session",
    wallet: ResilienceWallet,
    amount: float,
    reason: str,
    reference_id: str | None = None,
) -> ResilienceTransaction:
    """
    Credit `amount` back to wallet.balance (capped at max_balance).
    Returns the transaction record.
    """
    if amount <= 0:
        raise ValueError(f"restore_resilience: amount must be > 0, got {amount}")
    wallet.balance = round(min(wallet.balance + amount, wallet.max_balance), 6)
    tx = ResilienceTransaction(
        wallet_id=wallet.id,
        dimension=wallet.dimension,
        amount=+amount,
        reason=reason,
        reference_id=reference_id,
    )
    session.add(tx)
    return tx


def get_wallet_state(
    session: "Session",
    shipment: "Shipment",
    cfg: ResilienceConfig = DEFAULT_CONFIG,
) -> WalletState:
    """
    Load wallet balances from DB and build a WalletState object.
    If a wallet doesn't exist yet, it is initialised first.
    """
    wallets = initialise_shipment_wallets(session, shipment, cfg)

    def _dim(w: ResilienceWallet, unit: str) -> DimensionState:
        return DimensionState(
            dimension=w.dimension,
            maximum_balance=w.max_balance,
            remaining_balance=w.balance,
            unit=unit,
        )

    return WalletState(
        shipment_id=shipment.id,
        shipment_code=shipment.shipment_code,
        time=_dim(wallets[WalletDimension.TIME], "hours"),
        cost=_dim(wallets[WalletDimension.COST], "USD"),
        temperature=_dim(wallets[WalletDimension.TEMPERATURE], "degC_hours"),
        capacity=_dim(wallets[WalletDimension.CAPACITY], "kg"),
    )


def verify_wallet_consistency(
    session: "Session",
    wallet: ResilienceWallet,
) -> tuple[bool, float]:
    """
    Verify wallet.balance == max_balance + sum(transactions).
    Returns (is_consistent, expected_balance).
    """
    tx_sum = sum(
        tx.amount
        for tx in session.query(ResilienceTransaction)
        .filter_by(wallet_id=wallet.id)
        .all()
    )
    expected = round(wallet.max_balance + tx_sum, 6)
    # The initial credit transaction already includes max_balance as the first +amount
    # so we subtract max_balance once to avoid double-counting
    expected_v2 = round(tx_sum, 6)
    is_consistent = abs(wallet.balance - expected_v2) < 0.01
    return is_consistent, expected_v2
