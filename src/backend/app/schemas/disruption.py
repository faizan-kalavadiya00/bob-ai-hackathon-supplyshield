"""Pydantic schemas for Disruption Management API (Phase 4B)."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class DisruptionSummary(BaseModel):
    """Lightweight disruption record for list views."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    disruption_code: str
    name: str
    type: str
    severity: int
    affected_region: str
    status: str
    start_time: datetime
    end_time: Optional[datetime] = None
    description: Optional[str] = None
    # Computed aggregates
    affected_shipment_count: int
    total_cargo_exposure_usd: float
    avg_impact_score: float
    total_delay_hours: float
    duration_hours: float


class ShipmentImpactSchema(BaseModel):
    """One shipment's exposure to a disruption."""
    shipment_id: int
    shipment_code: str
    origin: str
    destination: str
    cargo_type: str
    cargo_value_usd: float
    weight_kg: float
    priority: str
    status: str
    temperature_sensitive: bool
    impact_score: float
    delay_hours: float


class DNASchema(BaseModel):
    """Full Disruption DNA fingerprint."""
    disruption_id: int
    type_score: float
    type_label: str
    severity_score: float
    severity_raw: int
    duration_score: float
    duration_hours: float
    geo_scope_score: float
    geo_scope_label: str
    transport_mode_score: float
    transport_mode_label: str
    capacity_impact_score: float
    port_relevance_score: float
    region_score: float
    region_label: str
    avg_impact_score: float
    affected_shipment_count: int
    dna_summary: Optional[str] = None
    generated_at: datetime


class DimensionMatchSchema(BaseModel):
    """One DNA dimension's contribution to similarity."""
    dimension: str
    weight: float
    subject_score: float
    candidate_score: float
    difference: float
    contribution: float
    match_quality: str


class SimilarityResultSchema(BaseModel):
    """Similarity between two disruptions."""
    disruption_id: int
    disruption_code: str
    name: str
    disruption_type: str
    severity: int
    affected_region: str
    status: str
    duration_hours: float
    similarity_score: float
    dimension_matches: list[DimensionMatchSchema]
    top_matching_dimensions: list[str]
    historical_outcome: Optional[str] = None


class CascadeNodeSchema(BaseModel):
    """A single node in the cascading impact tree."""
    level: str         # DISRUPTION / PORT_REGION / ROUTES / SHIPMENTS / CARGO / FLEET
    label: str
    detail: Optional[str] = None
    children: list["CascadeNodeSchema"] = []


CascadeNodeSchema.model_rebuild()


class DisruptionImpactSchema(BaseModel):
    """Full impact breakdown for one disruption."""
    disruption_id: int
    disruption_code: str
    name: str
    affected_shipments: list[ShipmentImpactSchema]
    total_cargo_exposure_usd: float
    affected_shipment_count: int
    temperature_sensitive_count: int
    total_delay_hours: float
    avg_impact_score: float
    cascade: CascadeNodeSchema


class DisruptionDetailSchema(BaseModel):
    """Full disruption detail response."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    disruption_code: str
    name: str
    type: str
    severity: int
    affected_region: str
    status: str
    start_time: datetime
    end_time: Optional[datetime] = None
    description: Optional[str] = None
    duration_hours: float
    # Aggregates
    affected_shipment_count: int
    total_cargo_exposure_usd: float
    avg_impact_score: float
    total_delay_hours: float
    temperature_sensitive_count: int
    # DNA
    dna: Optional[DNASchema] = None
