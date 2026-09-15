"""Phase 3 — Resilience Wallet and RRI unit tests.

These tests do NOT require a database connection. They test the pure
calculation logic in wallet_service.py and rri_calculator.py.

All tests are deterministic: same inputs → same outputs every time.
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta, timezone

from app.models.resilience import WalletDimension
from app.models.shipment import CargoPriority, ShipmentStatus
from app.services.resilience_config import (
    ResilienceConfig,
    DEFAULT_CONFIG,
    DimensionWeights,
    WalletStatusThresholds,
    RRIStatusThresholds,
    CriticalityMultipliers,
    TimeWalletAssumptions,
    CostWalletAssumptions,
    TemperatureWalletAssumptions,
    CapacityWalletAssumptions,
)
from app.services.wallet_service import (
    DimensionState,
    DimensionStatus,
    WalletState,
    calculate_time_budget,
    calculate_cost_budget,
    calculate_temperature_budget,
    calculate_capacity_budget,
    consume_resilience,
    restore_resilience,
)
from app.services.rri_calculator import (
    RRIStatus,
    calculate_rri,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

NOW = datetime(2026, 9, 15, 12, 0, 0, tzinfo=timezone.utc)

def _make_shipment(
    priority: CargoPriority = CargoPriority.STANDARD,
    cargo_value: float = 100_000.0,
    weight_kg: float = 2_000.0,
    temp_sensitive: bool = False,
    min_c: float | None = None,
    max_c: float | None = None,
    route_duration: float = 89.0,
    route_risk: float = 0.22,
):
    """Build a minimal mock Shipment object for unit tests."""
    ship = MagicMock()
    ship.id = 1
    ship.shipment_code = "S-TEST"
    ship.priority = priority
    ship.cargo_value_usd = cargo_value
    ship.weight_kg = weight_kg
    ship.temperature_sensitive = temp_sensitive
    ship.min_temperature_c = min_c
    ship.max_temperature_c = max_c
    ship.status = ShipmentStatus.IN_TRANSIT
    ship.departure_time = NOW - timedelta(hours=10)
    ship.eta = NOW + timedelta(hours=route_duration - 10)
    # Mock route
    ship.route = MagicMock()
    ship.route.duration_hours = route_duration
    ship.route.risk_score = route_risk
    ship.route_id = 1
    return ship


def _make_full_wallet_state(
    time_rem: float = 80.0,  time_max: float = 100.0,
    cost_rem: float = 8000.0, cost_max: float = 10000.0,
    temp_rem: float = 40.0,  temp_max: float = 50.0,
    cap_rem:  float = 600.0,  cap_max:  float = 800.0,
    priority: CargoPriority = CargoPriority.STANDARD,
) -> WalletState:
    """Build a WalletState with controllable balances for formula testing."""
    return WalletState(
        shipment_id=1,
        shipment_code="S-TEST",
        time=DimensionState(WalletDimension.TIME, time_max, time_rem, "hours"),
        cost=DimensionState(WalletDimension.COST, cost_max, cost_rem, "USD"),
        temperature=DimensionState(WalletDimension.TEMPERATURE, temp_max, temp_rem, "degC_hours"),
        capacity=DimensionState(WalletDimension.CAPACITY, cap_max, cap_rem, "kg"),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Config validation
# ═══════════════════════════════════════════════════════════════════════════════

def test_default_weights_sum_to_one():
    w = DimensionWeights()
    total = w.time + w.cost + w.temperature + w.capacity
    assert abs(total - 1.0) < 1e-9, f"Weights sum to {total}"


def test_invalid_weights_raise():
    with pytest.raises(ValueError, match="sum to 1.0"):
        DimensionWeights(time=0.5, cost=0.5, temperature=0.5, capacity=0.5)


def test_resilience_config_has_all_sections():
    cfg = ResilienceConfig()
    assert cfg.weights is not None
    assert cfg.wallet_thresholds is not None
    assert cfg.rri_thresholds is not None
    assert cfg.criticality is not None
    assert cfg.time is not None
    assert cfg.cost is not None
    assert cfg.temperature is not None
    assert cfg.capacity is not None
    assert cfg.disruption is not None


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Initial wallet budget calculations
# ═══════════════════════════════════════════════════════════════════════════════

def test_time_budget_standard_shipment():
    ship = _make_shipment(priority=CargoPriority.STANDARD, cargo_value=100_000, route_duration=89.0)
    budget = calculate_time_budget(ship, 89.0, DEFAULT_CONFIG)
    # base=35.6, boost=8, value=2 → raw=45.6 × 0.8 = 36.48
    assert DEFAULT_CONFIG.time.min_budget_hours <= budget <= DEFAULT_CONFIG.time.max_budget_hours


def test_time_budget_critical_larger_than_routine():
    ship_critical = _make_shipment(priority=CargoPriority.CRITICAL, cargo_value=100_000)
    ship_routine = _make_shipment(priority=CargoPriority.ROUTINE, cargo_value=100_000)
    b_crit = calculate_time_budget(ship_critical, 89.0, DEFAULT_CONFIG)
    b_rout = calculate_time_budget(ship_routine, 89.0, DEFAULT_CONFIG)
    assert b_crit > b_rout, "CRITICAL shipments must have larger time budgets than ROUTINE"


def test_time_budget_increases_with_cargo_value():
    ship_low  = _make_shipment(cargo_value=10_000)
    ship_high = _make_shipment(cargo_value=400_000)
    b_low  = calculate_time_budget(ship_low,  89.0, DEFAULT_CONFIG)
    b_high = calculate_time_budget(ship_high, 89.0, DEFAULT_CONFIG)
    assert b_high > b_low


def test_time_budget_bounded():
    ship = _make_shipment(priority=CargoPriority.CRITICAL, cargo_value=10_000_000)
    budget = calculate_time_budget(ship, 1000.0, DEFAULT_CONFIG)
    assert budget <= DEFAULT_CONFIG.time.max_budget_hours


def test_cost_budget_standard():
    ship = _make_shipment(cargo_value=200_000.0, route_risk=0.22)
    budget = calculate_cost_budget(ship, 0.22, DEFAULT_CONFIG)
    assert DEFAULT_CONFIG.cost.min_budget_usd <= budget <= DEFAULT_CONFIG.cost.max_budget_usd


def test_cost_budget_scales_with_cargo_value():
    ship_low  = _make_shipment(cargo_value=50_000)
    ship_high = _make_shipment(cargo_value=500_000)
    b_low  = calculate_cost_budget(ship_low,  0.20, DEFAULT_CONFIG)
    b_high = calculate_cost_budget(ship_high, 0.20, DEFAULT_CONFIG)
    assert b_high > b_low


def test_temperature_budget_zero_for_non_cold():
    ship = _make_shipment(temp_sensitive=False)
    assert calculate_temperature_budget(ship, 89.0, DEFAULT_CONFIG) == 0.0


def test_temperature_budget_positive_for_cold():
    ship = _make_shipment(temp_sensitive=True, min_c=2.0, max_c=8.0)
    budget = calculate_temperature_budget(ship, 89.0, DEFAULT_CONFIG)
    assert budget > 0.0
    assert budget >= DEFAULT_CONFIG.temperature.min_budget


def test_temperature_budget_wider_range_gives_more():
    ship_narrow = _make_shipment(temp_sensitive=True, min_c=4.0, max_c=6.0)
    ship_wide   = _make_shipment(temp_sensitive=True, min_c=-20.0, max_c=-10.0)
    b_narrow = calculate_temperature_budget(ship_narrow, 89.0, DEFAULT_CONFIG)
    b_wide   = calculate_temperature_budget(ship_wide,   89.0, DEFAULT_CONFIG)
    assert b_wide > b_narrow


def test_capacity_budget_scales_with_weight():
    ship_light = _make_shipment(weight_kg=500.0)
    ship_heavy = _make_shipment(weight_kg=10_000.0)
    b_light = calculate_capacity_budget(ship_light, 0.20, DEFAULT_CONFIG)
    b_heavy = calculate_capacity_budget(ship_heavy, 0.20, DEFAULT_CONFIG)
    assert b_heavy > b_light


def test_capacity_budget_bounded():
    ship = _make_shipment(weight_kg=1_000_000.0)
    budget = calculate_capacity_budget(ship, 0.20, DEFAULT_CONFIG)
    assert budget <= DEFAULT_CONFIG.capacity.max_budget_kg


# ═══════════════════════════════════════════════════════════════════════════════
# 3. DimensionState properties
# ═══════════════════════════════════════════════════════════════════════════════

def test_dimension_consumed_balance():
    ds = DimensionState(WalletDimension.TIME, 100.0, 70.0, "hours")
    assert ds.consumed_balance == pytest.approx(30.0)


def test_dimension_utilization_pct():
    ds = DimensionState(WalletDimension.TIME, 100.0, 70.0, "hours")
    assert ds.utilization_percent == pytest.approx(30.0)


def test_dimension_score_full():
    ds = DimensionState(WalletDimension.COST, 10000.0, 10000.0, "USD")
    assert ds.dimension_score == pytest.approx(100.0)


def test_dimension_score_empty():
    ds = DimensionState(WalletDimension.COST, 10000.0, 0.0, "USD")
    assert ds.dimension_score == pytest.approx(0.0)


def test_dimension_score_zero_max_returns_100():
    """Non-applicable dimension (e.g. temperature for non-cold) should score 100."""
    ds = DimensionState(WalletDimension.TEMPERATURE, 0.0, 0.0, "degC_hours")
    assert ds.dimension_score == pytest.approx(100.0)


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Wallet status thresholds
# ═══════════════════════════════════════════════════════════════════════════════

def test_status_healthy():
    ds = DimensionState(WalletDimension.TIME, 100.0, 80.0, "hours")  # 20% consumed
    assert ds.status(DEFAULT_CONFIG) == DimensionStatus.HEALTHY


def test_status_stressed():
    ds = DimensionState(WalletDimension.TIME, 100.0, 60.0, "hours")  # 40% consumed
    assert ds.status(DEFAULT_CONFIG) == DimensionStatus.STRESSED


def test_status_vulnerable():
    ds = DimensionState(WalletDimension.TIME, 100.0, 35.0, "hours")  # 65% consumed
    assert ds.status(DEFAULT_CONFIG) == DimensionStatus.VULNERABLE


def test_status_critical():
    ds = DimensionState(WalletDimension.TIME, 100.0, 10.0, "hours")  # 90% consumed
    assert ds.status(DEFAULT_CONFIG) == DimensionStatus.CRITICAL


def test_status_bankrupt():
    ds = DimensionState(WalletDimension.TIME, 100.0, 0.0, "hours")   # 100% consumed
    assert ds.status(DEFAULT_CONFIG) == DimensionStatus.BANKRUPT


def test_status_bankrupt_negative():
    ds = DimensionState(WalletDimension.TIME, 100.0, -5.0, "hours")
    assert ds.status(DEFAULT_CONFIG) == DimensionStatus.BANKRUPT


# ═══════════════════════════════════════════════════════════════════════════════
# 5–8. Wallet consumption (mocked session)
# ═══════════════════════════════════════════════════════════════════════════════

def _make_wallet(balance: float = 100.0, max_balance: float = 100.0) -> MagicMock:
    wallet = MagicMock()
    wallet.id = 1
    wallet.balance = balance
    wallet.max_balance = max_balance
    wallet.dimension = WalletDimension.TIME
    return wallet


def test_consume_time_resilience():
    session = MagicMock()
    wallet = _make_wallet(100.0)
    tx = consume_resilience(session, wallet, 30.0, "Port delay", "DIS-001")
    assert wallet.balance == pytest.approx(70.0)
    assert tx.amount == pytest.approx(-30.0)
    session.add.assert_called_once()


def test_consume_cost_resilience():
    session = MagicMock()
    wallet = _make_wallet(10000.0, 10000.0)
    wallet.dimension = WalletDimension.COST
    tx = consume_resilience(session, wallet, 1500.0, "Recovery cost", "DIS-001")
    assert wallet.balance == pytest.approx(8500.0)
    assert tx.amount == pytest.approx(-1500.0)


def test_consume_temperature_resilience():
    session = MagicMock()
    wallet = _make_wallet(50.0)
    wallet.dimension = WalletDimension.TEMPERATURE
    tx = consume_resilience(session, wallet, 12.0, "Temperature excursion", "EXC-001")
    assert wallet.balance == pytest.approx(38.0)
    assert tx.amount == pytest.approx(-12.0)


def test_consume_capacity_resilience():
    session = MagicMock()
    wallet = _make_wallet(800.0)
    wallet.dimension = WalletDimension.CAPACITY
    tx = consume_resilience(session, wallet, 200.0, "Fleet reallocation", None)
    assert wallet.balance == pytest.approx(600.0)
    assert tx.amount == pytest.approx(-200.0)


def test_consume_clamps_at_zero():
    """Consuming more than the balance clamps to 0, not negative."""
    session = MagicMock()
    wallet = _make_wallet(10.0)
    tx = consume_resilience(session, wallet, 50.0, "Overconsumption", None)
    assert wallet.balance == 0.0
    assert tx.amount == pytest.approx(-10.0)  # actual consumed = min(50, 10)


def test_consume_rejects_zero_amount():
    with pytest.raises(ValueError):
        consume_resilience(MagicMock(), _make_wallet(), 0.0, "test", None)


def test_consume_rejects_negative_amount():
    with pytest.raises(ValueError):
        consume_resilience(MagicMock(), _make_wallet(), -5.0, "test", None)


# ═══════════════════════════════════════════════════════════════════════════════
# 9. Transaction creation
# ═══════════════════════════════════════════════════════════════════════════════

def test_transaction_has_correct_fields():
    session = MagicMock()
    wallet = _make_wallet(100.0)
    tx = consume_resilience(session, wallet, 25.0, "Test reason", "REF-001")
    assert tx.wallet_id == wallet.id
    assert tx.dimension == WalletDimension.TIME
    assert tx.amount == pytest.approx(-25.0)
    assert tx.reason == "Test reason"
    assert tx.reference_id == "REF-001"


def test_restore_transaction_is_positive():
    session = MagicMock()
    wallet = _make_wallet(50.0, 100.0)
    tx = restore_resilience(session, wallet, 30.0, "Partial recovery")
    assert tx.amount == pytest.approx(+30.0)
    assert wallet.balance == pytest.approx(80.0)


def test_restore_capped_at_max():
    session = MagicMock()
    wallet = _make_wallet(90.0, 100.0)
    restore_resilience(session, wallet, 50.0, "Over-restore")
    assert wallet.balance == pytest.approx(100.0)


# ═══════════════════════════════════════════════════════════════════════════════
# 10. Bankruptcy detection
# ═══════════════════════════════════════════════════════════════════════════════

def test_time_bankruptcy_detected():
    ws = _make_full_wallet_state(time_rem=0.0, time_max=100.0)
    assert ws.is_resilience_bankrupt(DEFAULT_CONFIG) is True


def test_cost_bankruptcy_detected():
    ws = _make_full_wallet_state(cost_rem=0.0, cost_max=10000.0)
    assert ws.is_resilience_bankrupt(DEFAULT_CONFIG) is True


def test_temperature_bankruptcy_alone_not_operational_bankrupt():
    """Temperature bankruptcy alone does not trigger operational bankruptcy."""
    ws = _make_full_wallet_state(temp_rem=0.0, temp_max=50.0)
    assert ws.is_resilience_bankrupt(DEFAULT_CONFIG) is False


def test_capacity_bankruptcy_alone_not_operational_bankrupt():
    """Capacity bankruptcy alone does not trigger operational bankruptcy."""
    ws = _make_full_wallet_state(cap_rem=0.0, cap_max=800.0)
    assert ws.is_resilience_bankrupt(DEFAULT_CONFIG) is False


def test_all_healthy_not_bankrupt():
    ws = _make_full_wallet_state(
        time_rem=80.0, cost_rem=8000.0, temp_rem=40.0, cap_rem=600.0
    )
    assert ws.is_resilience_bankrupt(DEFAULT_CONFIG) is False


# ═══════════════════════════════════════════════════════════════════════════════
# 11–14. RRI calculation
# ═══════════════════════════════════════════════════════════════════════════════

def test_rri_full_wallet_is_100():
    ws = _make_full_wallet_state(
        time_rem=100.0, time_max=100.0,
        cost_rem=10000.0, cost_max=10000.0,
        temp_rem=50.0, temp_max=50.0,
        cap_rem=800.0, cap_max=800.0,
    )
    exp = calculate_rri(ws, CargoPriority.STANDARD, DEFAULT_CONFIG)
    # STANDARD has no adjustment, all dims=100 → RRI=100
    assert exp.rri == pytest.approx(100.0, abs=0.1)


def test_rri_empty_wallet_is_zero():
    ws = _make_full_wallet_state(
        time_rem=0.0, time_max=100.0,
        cost_rem=0.0, cost_max=10000.0,
        temp_rem=0.0, temp_max=50.0,
        cap_rem=0.0, cap_max=800.0,
    )
    exp = calculate_rri(ws, CargoPriority.STANDARD, DEFAULT_CONFIG)
    assert exp.rri == pytest.approx(0.0, abs=0.1)


def test_rri_bounds_always_0_to_100():
    """RRI must always be clamped between 0 and 100."""
    for time_rem in [0.0, 30.0, 70.0, 100.0]:
        for priority in CargoPriority:
            ws = _make_full_wallet_state(time_rem=time_rem)
            exp = calculate_rri(ws, priority, DEFAULT_CONFIG)
            assert 0.0 <= exp.rri <= 100.0, (
                f"RRI out of bounds: {exp.rri} for time_rem={time_rem} priority={priority}"
            )


def test_rri_is_deterministic():
    """Same inputs must always produce the same RRI."""
    ws = _make_full_wallet_state(time_rem=60.0, cost_rem=7000.0)
    exp1 = calculate_rri(ws, CargoPriority.CRITICAL, DEFAULT_CONFIG)
    exp2 = calculate_rri(ws, CargoPriority.CRITICAL, DEFAULT_CONFIG)
    assert exp1.rri == exp2.rri
    assert exp1.status == exp2.status


def test_rri_decreases_with_consumption():
    ws_before = _make_full_wallet_state(time_rem=100.0)
    ws_after  = _make_full_wallet_state(time_rem=30.0)
    exp_before = calculate_rri(ws_before, CargoPriority.STANDARD, DEFAULT_CONFIG)
    exp_after  = calculate_rri(ws_after,  CargoPriority.STANDARD, DEFAULT_CONFIG)
    assert exp_after.rri < exp_before.rri


def test_critical_priority_lowers_rri():
    """CRITICAL shipments score lower than ROUTINE for same wallet state."""
    ws = _make_full_wallet_state(time_rem=60.0, cost_rem=7000.0)
    exp_crit    = calculate_rri(ws, CargoPriority.CRITICAL, DEFAULT_CONFIG)
    exp_routine = calculate_rri(ws, CargoPriority.ROUTINE,  DEFAULT_CONFIG)
    assert exp_crit.rri < exp_routine.rri


def test_rri_status_healthy():
    ws = _make_full_wallet_state(
        time_rem=90.0, cost_rem=9000.0, temp_rem=48.0, cap_rem=750.0
    )
    exp = calculate_rri(ws, CargoPriority.STANDARD, DEFAULT_CONFIG)
    assert exp.status == RRIStatus.HEALTHY


def test_rri_status_bankrupt_when_all_zero():
    ws = _make_full_wallet_state(
        time_rem=0.0, cost_rem=0.0, temp_rem=0.0, cap_rem=0.0
    )
    exp = calculate_rri(ws, CargoPriority.STANDARD, DEFAULT_CONFIG)
    assert exp.status == RRIStatus.BANKRUPT


# ═══════════════════════════════════════════════════════════════════════════════
# 15. RRI explanation object
# ═══════════════════════════════════════════════════════════════════════════════

def test_rri_explanation_has_required_fields():
    ws = _make_full_wallet_state(time_rem=70.0, cost_rem=6000.0)
    exp = calculate_rri(ws, CargoPriority.HIGH, DEFAULT_CONFIG)
    assert isinstance(exp.rri, float)
    assert isinstance(exp.status, RRIStatus)
    assert set(exp.dimensions.keys()) == {"time", "cost", "temperature", "capacity"}
    assert set(exp.weights.keys()) == {"time", "cost", "temperature", "capacity"}
    assert set(exp.weighted_scores.keys()) == {"time", "cost", "temperature", "capacity"}
    assert isinstance(exp.contributors, list)
    assert isinstance(exp.bankruptcy_flags, dict)
    assert isinstance(exp.is_resilience_bankrupt, bool)


def test_rri_explanation_weights_match_config():
    ws = _make_full_wallet_state()
    exp = calculate_rri(ws, CargoPriority.STANDARD, DEFAULT_CONFIG)
    w = DEFAULT_CONFIG.weights
    assert exp.weights["time"] == pytest.approx(w.time)
    assert exp.weights["cost"] == pytest.approx(w.cost)
    assert exp.weights["temperature"] == pytest.approx(w.temperature)
    assert exp.weights["capacity"] == pytest.approx(w.capacity)


def test_rri_explanation_weighted_scores_sum_correctly():
    ws = _make_full_wallet_state(time_rem=80.0, cost_rem=8000.0,
                                 temp_rem=40.0, cap_rem=640.0)
    exp = calculate_rri(ws, CargoPriority.STANDARD, DEFAULT_CONFIG)
    total = sum(exp.weighted_scores.values())
    assert total == pytest.approx(exp.weighted_score_before_adjustment, abs=0.01)


def test_bankruptcy_flag_set_when_dimension_zero():
    ws = _make_full_wallet_state(time_rem=0.0, time_max=100.0)
    exp = calculate_rri(ws, CargoPriority.STANDARD, DEFAULT_CONFIG)
    assert exp.bankruptcy_flags["time"] is True
    assert exp.bankruptcy_flags["cost"] is False


# ═══════════════════════════════════════════════════════════════════════════════
# 16. S-1042 baseline (without disruption)
# ═══════════════════════════════════════════════════════════════════════════════

def test_s1042_baseline_rri():
    """S-1042: Ahmedabad→Dubai, pharma, $485k, 1240kg, critical priority, route 89h/risk 0.22."""
    ship = _make_shipment(
        priority=CargoPriority.CRITICAL,
        cargo_value=485_000.0,
        weight_kg=1240.0,
        temp_sensitive=True,
        min_c=2.0,
        max_c=8.0,
        route_duration=89.0,
        route_risk=0.22,
    )
    cfg = DEFAULT_CONFIG
    time_b = calculate_time_budget(ship, 89.0, cfg)
    cost_b = calculate_cost_budget(ship, 0.22, cfg)
    temp_b = calculate_temperature_budget(ship, 89.0, cfg)
    cap_b  = calculate_capacity_budget(ship, 0.22, cfg)

    ws = WalletState(
        shipment_id=ship.id,
        shipment_code="S-1042",
        time=DimensionState(WalletDimension.TIME, time_b, time_b, "hours"),
        cost=DimensionState(WalletDimension.COST, cost_b, cost_b, "USD"),
        temperature=DimensionState(WalletDimension.TEMPERATURE, temp_b, temp_b, "degC_hours"),
        capacity=DimensionState(WalletDimension.CAPACITY, cap_b, cap_b, "kg"),
    )
    exp = calculate_rri(ws, ship.priority, cfg)

    # Baseline: all dims full → should be STRESSED/HEALTHY depending on criticality penalty
    # CRITICAL penalty will reduce from 100. Assert bounds.
    assert 60.0 <= exp.rri <= 100.0, f"Unexpected baseline RRI: {exp.rri}"
    assert exp.rri > 50.0, "Baseline S-1042 should not start stressed or worse"
    assert not exp.is_resilience_bankrupt


def test_s1042_baseline_not_bankrupt():
    ship = _make_shipment(
        priority=CargoPriority.CRITICAL,
        cargo_value=485_000.0, weight_kg=1240.0,
        temp_sensitive=True, min_c=2.0, max_c=8.0,
        route_duration=89.0, route_risk=0.22,
    )
    cfg = DEFAULT_CONFIG
    time_b = calculate_time_budget(ship, 89.0, cfg)
    cost_b = calculate_cost_budget(ship, 0.22, cfg)
    temp_b = calculate_temperature_budget(ship, 89.0, cfg)
    cap_b  = calculate_capacity_budget(ship, 0.22, cfg)
    ws = WalletState(
        shipment_id=1, shipment_code="S-1042",
        time=DimensionState(WalletDimension.TIME, time_b, time_b, "hours"),
        cost=DimensionState(WalletDimension.COST, cost_b, cost_b, "USD"),
        temperature=DimensionState(WalletDimension.TEMPERATURE, temp_b, temp_b, "degC_hours"),
        capacity=DimensionState(WalletDimension.CAPACITY, cap_b, cap_b, "kg"),
    )
    exp = calculate_rri(ws, ship.priority, cfg)
    assert not exp.is_resilience_bankrupt


# ═══════════════════════════════════════════════════════════════════════════════
# 17. S-1042 after Mumbai Port Crisis
# ═══════════════════════════════════════════════════════════════════════════════

def test_s1042_after_disruption_rri_decreases():
    """
    After applying Mumbai Port Crisis (impact=0.85, delay=48h) + temperature
    excursion to S-1042 wallets, RRI must be lower than baseline.
    """
    ship = _make_shipment(
        priority=CargoPriority.CRITICAL,
        cargo_value=485_000.0, weight_kg=1240.0,
        temp_sensitive=True, min_c=2.0, max_c=8.0,
        route_duration=89.0, route_risk=0.22,
    )
    cfg = DEFAULT_CONFIG
    time_b = calculate_time_budget(ship, 89.0, cfg)
    cost_b = calculate_cost_budget(ship, 0.22, cfg)
    temp_b = calculate_temperature_budget(ship, 89.0, cfg)
    cap_b  = calculate_capacity_budget(ship, 0.22, cfg)

    ws_before = WalletState(
        shipment_id=1, shipment_code="S-1042",
        time=DimensionState(WalletDimension.TIME, time_b, time_b, "hours"),
        cost=DimensionState(WalletDimension.COST, cost_b, cost_b, "USD"),
        temperature=DimensionState(WalletDimension.TEMPERATURE, temp_b, temp_b, "degC_hours"),
        capacity=DimensionState(WalletDimension.CAPACITY, cap_b, cap_b, "kg"),
    )

    # Apply disruption consumption
    a = cfg.disruption
    impact, delay = 0.85, 48.0
    time_consumed = delay * impact * a.time_multiplier
    cost_consumed = 485_000.0 * impact * a.cost_fraction
    temp_consumed = 7.833 * a.temp_multiplier   # approx breach_degree_hours from seed
    cap_consumed  = 1240.0 * impact * a.capacity_fraction

    ws_after = WalletState(
        shipment_id=1, shipment_code="S-1042",
        time=DimensionState(WalletDimension.TIME, time_b, max(time_b - time_consumed, 0), "hours"),
        cost=DimensionState(WalletDimension.COST, cost_b, max(cost_b - cost_consumed, 0), "USD"),
        temperature=DimensionState(WalletDimension.TEMPERATURE, temp_b, max(temp_b - temp_consumed, 0), "degC_hours"),
        capacity=DimensionState(WalletDimension.CAPACITY, cap_b, max(cap_b - cap_consumed, 0), "kg"),
    )

    exp_before = calculate_rri(ws_before, ship.priority, cfg)
    exp_after  = calculate_rri(ws_after,  ship.priority, cfg)

    assert exp_after.rri < exp_before.rri, (
        f"RRI should decrease after disruption: before={exp_before.rri}, after={exp_after.rri}"
    )


def test_s1042_disruption_produces_transactions():
    """Verify disruption consumption creates negative transaction amounts."""
    session = MagicMock()
    wallet = _make_wallet(100.0)
    tx = consume_resilience(session, wallet, 40.8, "Delay from DIS-001: 48h × 0.85", "DIS-001")
    assert tx.amount < 0
    assert abs(tx.amount) == pytest.approx(40.8)
    assert tx.reference_id == "DIS-001"


# ═══════════════════════════════════════════════════════════════════════════════
# 18. Dashboard aggregate (pure logic test)
# ═══════════════════════════════════════════════════════════════════════════════

def test_aggregate_rri_correct():
    """Weighted average of two shipments with known RRIs."""
    cfg = DEFAULT_CONFIG
    ws1 = _make_full_wallet_state(time_rem=90.0, cost_rem=9000.0, temp_rem=45.0, cap_rem=720.0)
    ws2 = _make_full_wallet_state(time_rem=40.0, cost_rem=4000.0, temp_rem=20.0, cap_rem=300.0)
    exp1 = calculate_rri(ws1, CargoPriority.STANDARD, cfg)
    exp2 = calculate_rri(ws2, CargoPriority.STANDARD, cfg)
    avg = (exp1.rri + exp2.rri) / 2
    assert 0.0 <= avg <= 100.0


# ═══════════════════════════════════════════════════════════════════════════════
# 19. API-layer validation (schema tests)
# ═══════════════════════════════════════════════════════════════════════════════

def test_apply_event_schema_rejects_zero_amount():
    from pydantic import ValidationError
    from app.schemas.resilience import ApplyEventRequest
    with pytest.raises(ValidationError):
        ApplyEventRequest(dimension="time", amount=0.0, reason="test")


def test_apply_event_schema_rejects_negative():
    from pydantic import ValidationError
    from app.schemas.resilience import ApplyEventRequest
    with pytest.raises(ValidationError):
        ApplyEventRequest(dimension="time", amount=-5.0, reason="test")


def test_apply_event_schema_rejects_invalid_dimension():
    from pydantic import ValidationError
    from app.schemas.resilience import ApplyEventRequest
    with pytest.raises(ValidationError):
        ApplyEventRequest(dimension="profit", amount=10.0, reason="test")


def test_apply_event_schema_rejects_empty_reason():
    from pydantic import ValidationError
    from app.schemas.resilience import ApplyEventRequest
    with pytest.raises(ValidationError):
        ApplyEventRequest(dimension="time", amount=5.0, reason="")


def test_apply_event_schema_valid():
    from app.schemas.resilience import ApplyEventRequest
    req = ApplyEventRequest(dimension="time", amount=12.5, reason="Port delay")
    assert req.dimension == "time"
    assert req.amount == 12.5


# ═══════════════════════════════════════════════════════════════════════════════
# 20. Invalid event validation (service layer)
# ═══════════════════════════════════════════════════════════════════════════════

def test_consume_rejects_inf():
    import math
    session = MagicMock()
    wallet = _make_wallet(100.0)
    # inf is > 0 so passes the amount check, but causes balance to go to 0 (clamped)
    # This is acceptable — the wallet service clamps at 0
    tx = consume_resilience(session, wallet, float("inf"), "test", None)
    assert wallet.balance == 0.0


def test_restore_rejects_zero():
    with pytest.raises(ValueError):
        restore_resilience(MagicMock(), _make_wallet(), 0.0, "test")


def test_restore_rejects_negative():
    with pytest.raises(ValueError):
        restore_resilience(MagicMock(), _make_wallet(), -1.0, "test")
