"""Pydantic schemas for the Resilience Wallet and RRI API."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


# ── Dimension schemas ─────────────────────────────────────────────────────────

class DimensionStateSchema(BaseModel):
    dimension: str
    maximum_balance: float
    remaining_balance: float
    consumed_balance: float
    utilization_percent: float
    dimension_score: float
    status: str
    unit: str


class WalletStateSchema(BaseModel):
    shipment_id: int
    shipment_code: str
    time: DimensionStateSchema
    cost: DimensionStateSchema
    temperature: DimensionStateSchema
    capacity: DimensionStateSchema
    is_resilience_bankrupt: bool
    computed_at: datetime


# ── RRI schemas ───────────────────────────────────────────────────────────────

class ContributorSchema(BaseModel):
    factor: str
    impact: float
    reason: str
    severity: str


class RRIExplanationSchema(BaseModel):
    rri: float
    status: str
    dimensions: dict[str, float]
    weights: dict[str, float]
    weighted_scores: dict[str, float]
    contributors: list[ContributorSchema]
    criticality_adjustment: float
    weighted_score_before_adjustment: float
    bankruptcy_flags: dict[str, bool]
    is_resilience_bankrupt: bool
    shipment_priority: str
    computed_at: str


# ── Combined response ─────────────────────────────────────────────────────────

class ResilienceResponse(BaseModel):
    wallet: WalletStateSchema
    rri: RRIExplanationSchema


# ── Transactions ──────────────────────────────────────────────────────────────

class TransactionSchema(BaseModel):
    id: int
    wallet_id: int
    dimension: str
    amount: float
    reason: str
    reference_id: str | None
    timestamp: datetime

    model_config = {"from_attributes": True}


# ── Apply-event request ───────────────────────────────────────────────────────

class ApplyEventRequest(BaseModel):
    dimension: Literal["time", "cost", "temperature", "capacity"]
    amount: float = Field(gt=0, description="Amount to consume (must be positive)")
    reason: str = Field(min_length=3, max_length=500)
    reference_id: str | None = Field(default=None, max_length=100)

    @field_validator("amount")
    @classmethod
    def amount_must_be_finite(cls, v: float) -> float:
        import math
        if not math.isfinite(v):
            raise ValueError("amount must be a finite number")
        return v


# ── Dashboard aggregate ───────────────────────────────────────────────────────

class RRISummarySchema(BaseModel):
    total_shipments_assessed: int
    average_rri: float
    healthy_count: int
    stressed_count: int
    vulnerable_count: int
    critical_count: int
    bankrupt_count: int
    resilience_bankruptcies: int
    computed_at: datetime
