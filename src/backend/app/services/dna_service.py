"""SupplyShield Disruption DNA Service.

Generates deterministic DNA fingerprints from disruption records.
All values are computed from database attributes — no LLM, no ML.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.disruption import Disruption
from app.models.disruption_dna import DisruptionDNA
from app.models.shipment import Shipment
from app.models.disruption import ShipmentDisruption
from app.services.dna_config import (
    DISRUPTION_TYPE_SCORES,
    DNAConfig,
    classify_geo_scope,
    classify_port_relevance,
    classify_transport_mode,
    compute_capacity_impact,
    compute_region_score,
    normalize_duration,
)


def _compute_avg_impact(session: Session, disruption_id: int) -> tuple[float, int]:
    """Return (avg_impact_score, affected_count) from shipment_disruptions."""
    links = (
        session.query(ShipmentDisruption)
        .filter(ShipmentDisruption.disruption_id == disruption_id)
        .all()
    )
    if not links:
        return 0.0, 0
    total = sum(lnk.impact_score for lnk in links)
    return round(total / len(links), 4), len(links)


def _compute_duration(dis: Disruption) -> float:
    """Return disruption duration in hours from DB fields."""
    if dis.end_time and dis.start_time:
        delta = dis.end_time - dis.start_time
        return max(0.0, delta.total_seconds() / 3600.0)
    # Active disruptions without end_time: use time since start
    now = datetime.now(timezone.utc)
    start = dis.start_time
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    elapsed = (now - start).total_seconds() / 3600.0
    return max(0.0, elapsed)


def generate_dna(session: Session, disruption: Disruption, cfg: DNAConfig) -> DisruptionDNA:
    """
    Compute or update a DisruptionDNA record for the given disruption.

    If a record already exists it is updated in-place (idempotent).
    The session must be flushed/committed by the caller.
    """
    # ── Fetch existing or create new ──────────────────────────────────────────
    existing = (
        session.query(DisruptionDNA)
        .filter(DisruptionDNA.disruption_id == disruption.id)
        .first()
    )

    type_str = disruption.type.value if hasattr(disruption.type, "value") else str(disruption.type)
    type_score = DISRUPTION_TYPE_SCORES.get(type_str, 0.5)

    severity_raw = disruption.severity
    severity_score = round(severity_raw / 10.0, 4)

    duration_h = _compute_duration(disruption)
    duration_score = round(normalize_duration(duration_h), 4)

    geo_scope_label, geo_scope_score = classify_geo_scope(disruption.affected_region)
    transport_label, transport_score = classify_transport_mode(
        type_str, disruption.affected_region
    )
    port_relevance = classify_port_relevance(type_str, disruption.affected_region)
    capacity_impact = round(compute_capacity_impact(severity_raw, type_str), 4)
    region_score = compute_region_score(disruption.affected_region)

    avg_impact, affected_count = _compute_avg_impact(session, disruption.id)

    # Build human-readable DNA summary
    summary = (
        f"Type:{type_str.upper()} | Sev:{severity_raw}/10 | "
        f"Dur:{duration_h:.0f}h | Scope:{geo_scope_label} | "
        f"Mode:{transport_label.upper()} | "
        f"PortRel:{port_relevance:.2f} | "
        f"CapImpact:{capacity_impact:.2f} | "
        f"Affected:{affected_count} shipments"
    )

    if existing:
        existing.type_score = type_score
        existing.type_label = type_str
        existing.severity_score = severity_score
        existing.severity_raw = severity_raw
        existing.duration_score = duration_score
        existing.duration_hours = duration_h
        existing.geo_scope_score = geo_scope_score
        existing.geo_scope_label = geo_scope_label
        existing.transport_mode_score = transport_score
        existing.transport_mode_label = transport_label
        existing.capacity_impact_score = capacity_impact
        existing.port_relevance_score = port_relevance
        existing.region_score = region_score
        existing.region_label = disruption.affected_region
        existing.avg_impact_score = avg_impact
        existing.affected_shipment_count = affected_count
        existing.dna_summary = summary
        existing.generated_at = datetime.now(timezone.utc)
        return existing

    dna = DisruptionDNA(
        disruption_id=disruption.id,
        type_score=type_score,
        type_label=type_str,
        severity_score=severity_score,
        severity_raw=severity_raw,
        duration_score=duration_score,
        duration_hours=duration_h,
        geo_scope_score=geo_scope_score,
        geo_scope_label=geo_scope_label,
        transport_mode_score=transport_score,
        transport_mode_label=transport_label,
        capacity_impact_score=capacity_impact,
        port_relevance_score=port_relevance,
        region_score=region_score,
        region_label=disruption.affected_region,
        avg_impact_score=avg_impact,
        affected_shipment_count=affected_count,
        dna_summary=summary,
    )
    session.add(dna)
    return dna


def get_or_generate_dna(session: Session, disruption: Disruption, cfg: DNAConfig) -> DisruptionDNA:
    """Return cached DNA if up to date, else regenerate."""
    if disruption.dna is not None:
        return disruption.dna
    return generate_dna(session, disruption, cfg)
