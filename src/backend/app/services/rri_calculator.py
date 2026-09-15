"""SupplyShield Resilience Remaining Index (RRI) Calculator.

RRI is a 0–100 score representing the shipment's remaining resilience capital.

Formula (SupplyShield RRI):
─────────────────────────────────────────────────────────────────────────────
1.  For each dimension d ∈ {time, cost, temperature, capacity}:
      dim_score(d) = remaining_balance(d) / max_balance(d) × 100
      (clamped 0–100; non-applicable dimensions score 100)

2.  Weighted raw score:
      weighted_score = Σ weight(d) × dim_score(d)
                       where weights sum to 1.0

3.  Criticality adjustment:
      adjustment = (criticality_multiplier - 1.0) × weighted_score × adj_factor
      where adj_factor = 0.10  (10% modulation per criticality step)
      CRITICAL shipments are penalised further because failure consequences are severe.

4.  Adjusted score:
      adjusted = weighted_score - adjustment   (CRITICAL shipments score lower)
      adjusted = weighted_score + |adjustment| (ROUTINE shipments score slightly higher)

5.  Final RRI:
      RRI = round(clamp(adjusted, 0, 100))

This is the "SupplyShield Resilience Remaining Index (RRI)".
It is NOT an industry-standard metric. It is an internally consistent,
transparent, deterministic scoring model for the SupplyShield prototype.
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field

from app.models.shipment import CargoPriority
from app.services.resilience_config import ResilienceConfig, DEFAULT_CONFIG
from app.services.wallet_service import (
    DimensionState,
    DimensionStatus,
    WalletState,
)

# Criticality adjustment factor — how much priority modulates the final score.
# 0.10 means each priority step above STANDARD reduces the score by ~10% of
# the weighted score, reflecting the higher consequence of failure.
_CRITICALITY_ADJ_FACTOR = 0.10

# Priority ordinals (ROUTINE=0, STANDARD=1, HIGH=2, CRITICAL=3)
_PRIORITY_ORDINAL = {
    CargoPriority.ROUTINE: 0,
    CargoPriority.STANDARD: 1,
    CargoPriority.HIGH: 2,
    CargoPriority.CRITICAL: 3,
}


class RRIStatus(str, enum.Enum):
    HEALTHY = "HEALTHY"
    STRESSED = "STRESSED"
    VULNERABLE = "VULNERABLE"
    CRITICAL = "CRITICAL"
    BANKRUPT = "BANKRUPT"


@dataclass
class DimensionContribution:
    """Positive or negative contributor to the final RRI."""
    dimension: str
    score: float               # 0–100 dimension score
    weighted_contribution: float  # weight × score
    status: DimensionStatus
    bankruptcy_flag: bool = False


@dataclass
class RRIExplanation:
    """
    Full, explainable RRI result object.

    All fields are computed values — no LLM-generated numbers.
    """
    rri: float                                        # 0–100
    status: RRIStatus
    dimensions: dict[str, float]                      # dim_name → 0–100 score
    weights: dict[str, float]                         # dim_name → weight
    weighted_scores: dict[str, float]                 # dim_name → weight × score
    contributors: list[dict]                          # explanatory factors
    criticality_adjustment: float                     # how much priority changed the score
    weighted_score_before_adjustment: float
    bankruptcy_flags: dict[str, bool]                 # dim_name → is_bankrupt
    is_resilience_bankrupt: bool
    shipment_priority: str
    computed_at: str


def _rri_status(rri: float, cfg: ResilienceConfig) -> RRIStatus:
    t = cfg.rri_thresholds
    if rri >= t.healthy_min:
        return RRIStatus.HEALTHY
    if rri >= t.stressed_min:
        return RRIStatus.STRESSED
    if rri >= t.vulnerable_min:
        return RRIStatus.VULNERABLE
    if rri >= t.critical_min:
        return RRIStatus.CRITICAL
    return RRIStatus.BANKRUPT


def calculate_rri(
    wallet_state: WalletState,
    priority: CargoPriority,
    cfg: ResilienceConfig = DEFAULT_CONFIG,
) -> RRIExplanation:
    """
    Compute the SupplyShield RRI for a shipment given its wallet state.

    This is the single source of truth for RRI. It is pure Python —
    no database access, no randomness, fully deterministic.
    """
    from datetime import datetime, timezone

    w = cfg.weights
    dim_weights = {
        "time":        w.time,
        "cost":        w.cost,
        "temperature": w.temperature,
        "capacity":    w.capacity,
    }
    dim_states: dict[str, DimensionState] = {
        "time":        wallet_state.time,
        "cost":        wallet_state.cost,
        "temperature": wallet_state.temperature,
        "capacity":    wallet_state.capacity,
    }

    # 1. Dimension scores
    dim_scores: dict[str, float] = {
        name: state.dimension_score
        for name, state in dim_states.items()
    }

    # 2. Weighted scores
    weighted: dict[str, float] = {
        name: round(dim_weights[name] * dim_scores[name], 4)
        for name in dim_weights
    }
    weighted_total = round(sum(weighted.values()), 4)

    # 3. Criticality adjustment
    # STANDARD (ordinal 1) is baseline — no adjustment.
    # CRITICAL (ordinal 3) gets penalised; ROUTINE (ordinal 0) gets bonus.
    priority_ordinal = _PRIORITY_ORDINAL[priority]
    baseline_ordinal = 1  # STANDARD
    delta_ordinal = priority_ordinal - baseline_ordinal
    # Positive delta_ordinal = higher criticality = downward adjustment
    adjustment = delta_ordinal * _CRITICALITY_ADJ_FACTOR * weighted_total
    adjusted = weighted_total - adjustment

    # 4. Final RRI
    rri = round(max(0.0, min(adjusted, 100.0)), 2)

    # 5. Status
    status = _rri_status(rri, cfg)

    # 6. Bankruptcy flags
    bankruptcy_flags = {
        name: (state.remaining_balance <= 0 and state.maximum_balance > 0)
        for name, state in dim_states.items()
    }
    is_bankrupt = wallet_state.is_resilience_bankrupt(cfg)

    # 7. Explanatory contributors
    contributors: list[dict] = []
    for name, state in dim_states.items():
        dim_status = state.status(cfg)
        if dim_status in (DimensionStatus.CRITICAL, DimensionStatus.BANKRUPT):
            contributors.append({
                "factor": name,
                "impact": round(-((100.0 - dim_scores[name]) * dim_weights[name]), 2),
                "reason": (
                    f"{name.capitalize()} resilience is {dim_status.value.lower()} "
                    f"({state.utilization_percent:.1f}% consumed)"
                ),
                "severity": dim_status.value,
            })
        elif dim_status == DimensionStatus.HEALTHY and dim_scores[name] >= 80:
            contributors.append({
                "factor": name,
                "impact": round((dim_scores[name] - 75) * dim_weights[name], 2),
                "reason": (
                    f"{name.capitalize()} resilience is strong "
                    f"({state.utilization_percent:.1f}% consumed)"
                ),
                "severity": dim_status.value,
            })
    if delta_ordinal > 0:
        contributors.append({
            "factor": "criticality",
            "impact": round(-adjustment, 2),
            "reason": (
                f"Priority {priority.value.upper()} applies a criticality penalty "
                f"({delta_ordinal} level(s) above STANDARD)"
            ),
            "severity": "INFO",
        })

    return RRIExplanation(
        rri=rri,
        status=status,
        dimensions=dim_scores,
        weights=dict(dim_weights),
        weighted_scores=weighted,
        contributors=contributors,
        criticality_adjustment=round(-adjustment, 4),
        weighted_score_before_adjustment=weighted_total,
        bankruptcy_flags=bankruptcy_flags,
        is_resilience_bankrupt=is_bankrupt,
        shipment_priority=priority.value,
        computed_at=datetime.now(timezone.utc).isoformat(),
    )
