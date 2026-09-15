"""SupplyShield Resilience Configuration.

All thresholds, weights, and conversion assumptions are defined here.
No magic numbers are scattered through the codebase.

These are documented as:
  "SupplyShield configurable resilience model assumptions."

They do not claim to be industry-standard values. They are a transparent,
internally consistent set of parameters that make the model deterministic
and explainable for the SupplyShield prototype.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class DimensionWeights:
    """
    RRI dimension weights (must sum to 1.0).

    Rationale:
      TIME     0.35 — schedule adherence is the primary operational concern
      COST     0.25 — financial exposure drives recovery decisions
      TEMPERATURE 0.25 — cold-chain integrity is a compliance/safety issue
      CAPACITY 0.15 — spare logistics capacity is the most fungible resource
    """
    time: float = 0.35
    cost: float = 0.25
    temperature: float = 0.25
    capacity: float = 0.15

    def __post_init__(self) -> None:
        total = self.time + self.cost + self.temperature + self.capacity
        if abs(total - 1.0) > 1e-9:
            raise ValueError(f"Dimension weights must sum to 1.0, got {total}")


@dataclass(frozen=True)
class WalletStatusThresholds:
    """
    Utilization thresholds that determine dimension status.

    utilization_pct = consumed / max_balance * 100

    HEALTHY     0   – healthy_max
    STRESSED    healthy_max  – stressed_max
    VULNERABLE  stressed_max – vulnerable_max
    CRITICAL    vulnerable_max – 99.9
    BANKRUPT    100+
    """
    healthy_max: float = 25.0      # consumed ≤ 25%
    stressed_max: float = 50.0     # consumed 26–50%
    vulnerable_max: float = 75.0   # consumed 51–75%
    critical_max: float = 100.0    # consumed 76–100%
    # BANKRUPT when balance ≤ 0


@dataclass(frozen=True)
class RRIStatusThresholds:
    """
    Overall RRI score brackets → shipment resilience status.

    HEALTHY    rri ≥ 75
    STRESSED   50 ≤ rri < 75
    VULNERABLE 25 ≤ rri < 50
    CRITICAL   10 ≤ rri < 25
    BANKRUPT   rri < 10
    """
    healthy_min: float = 75.0
    stressed_min: float = 50.0
    vulnerable_min: float = 25.0
    critical_min: float = 10.0


@dataclass(frozen=True)
class CriticalityMultipliers:
    """
    Shipment priority multipliers applied to initial wallet budgets.

    Higher-priority shipments start with proportionally larger budgets
    because the operational consequence of failure is greater.

    Assumption: a CRITICAL shipment warrants 2× the baseline resilience
    budget vs a ROUTINE shipment.
    """
    routine: float = 0.60
    standard: float = 0.80
    high: float = 1.10
    critical: float = 1.40


@dataclass(frozen=True)
class TimeWalletAssumptions:
    """
    Assumptions for the TIME dimension initial budget.

    Baseline time budget = route_duration_hours × route_slack_factor
    The budget represents the number of delay-hours the shipment can
    absorb before it is considered to have lost all time resilience.

    route_slack_factor: baseline slack expressed as a fraction of route duration.
      e.g. 0.40 means a 100h route gets a 40h time budget.

    priority_boost_hours: flat additional hours granted by priority level.
    cargo_value_time_factor: each USD 100k of cargo value adds this many hours.
      Rationale: high-value cargo justifies expedited recovery, giving more
      effective time resilience.
    """
    route_slack_factor: float = 0.40
    priority_boost_hours_per_level: float = 8.0   # per priority level above ROUTINE
    cargo_value_time_factor: float = 2.0           # hours per USD 100k
    min_budget_hours: float = 12.0
    max_budget_hours: float = 240.0


@dataclass(frozen=True)
class CostWalletAssumptions:
    """
    Assumptions for the COST dimension initial budget (USD).

    Baseline cost budget = cargo_value × value_fraction
    The budget represents the financial resilience capital — how much
    can be spent on recovery actions before the operation becomes
    financially unviable.

    value_fraction: fraction of cargo value treated as resilience budget.
      Rationale: operators typically accept spending up to 15% of cargo
      value on recovery before considering the shipment at risk.

    route_risk_surcharge: additional fraction added for higher-risk routes.
      Rationale: riskier routes justify a higher pre-allocated cost buffer.
    """
    value_fraction: float = 0.15
    route_risk_surcharge_per_unit: float = 0.05   # per 0.1 of route risk_score
    min_budget_usd: float = 5_000.0
    max_budget_usd: float = 500_000.0


@dataclass(frozen=True)
class TemperatureWalletAssumptions:
    """
    Assumptions for the TEMPERATURE dimension initial budget (°C·hours).

    Only populated for temperature-sensitive shipments.
    For non-temperature-sensitive shipments: budget = 0, balance = 0.

    Unit: degree-celsius-hours (the integral of temperature above max
    or below min over time).

    allowable_excursion_rate: the acceptable °C deviation from midpoint
      for the entire route duration, expressed as °C per hour.
      Budget = route_duration_hours × allowable_excursion_rate

    temp_range_bonus: a wider allowable range gives extra budget.
      Wider range = more tolerance before a reading is "outside spec".
      Bonus = (max_c - min_c) × range_multiplier (°C·hours per °C of range).
    """
    allowable_excursion_rate: float = 0.10    # °C·h per hour of transit
    range_multiplier: float = 5.0             # °C·h per °C of allowed range
    min_budget: float = 10.0
    max_budget: float = 2_000.0

    # Consumption: each cold-chain breach reading costs this per °C of excursion
    breach_cost_per_degree_per_reading: float = 1.0


@dataclass(frozen=True)
class CapacityWalletAssumptions:
    """
    Assumptions for the CAPACITY dimension initial budget (kg).

    Represents the spare logistics capacity available to re-route or
    substitute cargo if the primary carrier is disrupted.

    The baseline budget is the weight of the shipment multiplied by a
    redundancy factor — how many times over the shipment weight we
    have in reserve capacity in the network.

    redundancy_factor: 0.50 means 50% of shipment weight is available
      as spare capacity in the surrounding fleet/routes.
    """
    redundancy_factor: float = 0.50
    route_risk_reduction: float = 0.10   # per 0.1 of route risk score
    min_budget_kg: float = 500.0
    max_budget_kg: float = 50_000.0


@dataclass(frozen=True)
class DisruptionConsumptionAssumptions:
    """
    How a disruption event's (impact_score, delay_hours) is converted
    to resilience consumption across dimensions.

    All conversions are linear and deterministic.

    time_hours_consumed = delay_hours * impact_score * time_multiplier
    cost_consumed       = cargo_value_usd * impact_score * cost_fraction
    temperature_consumed= (breach_degree_hours from DB readings) * temp_multiplier
    capacity_consumed   = weight_kg * impact_score * capacity_fraction
    """
    time_multiplier: float = 1.0       # delay_hours × impact → TIME hours consumed
    cost_fraction: float = 0.08        # cargo_value × impact → COST consumed
    temp_multiplier: float = 1.0       # °C·h of excursions → TEMP consumed
    capacity_fraction: float = 0.20    # weight_kg × impact → CAPACITY consumed


@dataclass(frozen=True)
class ResilienceConfig:
    """
    Top-level configuration object holding all SupplyShield
    resilience model parameters.

    Instantiate once and pass through the service layer.
    Override individual nested dataclasses for testing or alternative
    model configurations.
    """
    weights: DimensionWeights = field(default_factory=DimensionWeights)
    wallet_thresholds: WalletStatusThresholds = field(default_factory=WalletStatusThresholds)
    rri_thresholds: RRIStatusThresholds = field(default_factory=RRIStatusThresholds)
    criticality: CriticalityMultipliers = field(default_factory=CriticalityMultipliers)
    time: TimeWalletAssumptions = field(default_factory=TimeWalletAssumptions)
    cost: CostWalletAssumptions = field(default_factory=CostWalletAssumptions)
    temperature: TemperatureWalletAssumptions = field(default_factory=TemperatureWalletAssumptions)
    capacity: CapacityWalletAssumptions = field(default_factory=CapacityWalletAssumptions)
    disruption: DisruptionConsumptionAssumptions = field(
        default_factory=DisruptionConsumptionAssumptions
    )


# Module-level default instance — used by all services unless overridden.
DEFAULT_CONFIG = ResilienceConfig()
