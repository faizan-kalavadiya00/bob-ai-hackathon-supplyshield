"""Disruption Management API router (Phase 4B).

All values come from the PostgreSQL database.
DNA and similarity scores are computed deterministically — no LLM.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.disruption import Disruption, ShipmentDisruption, DisruptionStatus
from app.models.shipment import Shipment
from app.schemas.disruption import (
    CascadeNodeSchema,
    DisruptionDetailSchema,
    DisruptionImpactSchema,
    DisruptionSummary,
    DNASchema,
    DimensionMatchSchema,
    ShipmentImpactSchema,
    SimilarityResultSchema,
)
from app.services.dna_config import DEFAULT_DNA_CONFIG
from app.services.dna_service import generate_dna
from app.services.similarity_service import find_similar_disruptions

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/disruptions", tags=["Disruptions"])

cfg = DEFAULT_DNA_CONFIG


# ── Helper: compute aggregates for one disruption ─────────────────────────────

def _aggregate_disruption(
    session: Session, dis: Disruption
) -> tuple[int, float, float, float, int]:
    """
    Returns (affected_count, total_cargo_usd, avg_impact, total_delay_h, temp_sensitive_count).
    All values computed from shipment_disruptions + shipments tables.
    """
    links: list[ShipmentDisruption] = (
        session.query(ShipmentDisruption)
        .filter(ShipmentDisruption.disruption_id == dis.id)
        .all()
    )
    if not links:
        return 0, 0.0, 0.0, 0.0, 0

    total_cargo = 0.0
    total_delay = 0.0
    total_impact = 0.0
    temp_count = 0

    for lnk in links:
        ship: Shipment | None = session.get(Shipment, lnk.shipment_id)
        if ship is None:
            continue
        total_cargo += float(ship.cargo_value_usd)
        total_delay += lnk.delay_hours
        total_impact += lnk.impact_score
        if ship.temperature_sensitive:
            temp_count += 1

    n = len(links)
    return (
        n,
        round(total_cargo, 2),
        round(total_impact / n, 4) if n else 0.0,
        round(total_delay, 2),
        temp_count,
    )


def _duration_hours(dis: Disruption) -> float:
    if dis.end_time and dis.start_time:
        d = dis.end_time - dis.start_time
        return max(0.0, d.total_seconds() / 3600.0)
    now = datetime.now(timezone.utc)
    start = dis.start_time
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    elapsed = (now - start).total_seconds() / 3600.0
    return max(0.0, elapsed)


def _build_cascade(session: Session, dis: Disruption) -> CascadeNodeSchema:
    """Build cascading impact tree from real DB relationships."""
    type_str = dis.type.value if hasattr(dis.type, "value") else str(dis.type)
    links: list[ShipmentDisruption] = (
        session.query(ShipmentDisruption)
        .filter(ShipmentDisruption.disruption_id == dis.id)
        .all()
    )

    # Leaf: shipments and their cargo
    shipment_nodes: list[CascadeNodeSchema] = []
    for lnk in links:
        ship: Shipment | None = session.get(Shipment, lnk.shipment_id)
        if ship is None:
            continue
        cargo_node = CascadeNodeSchema(
            level="CARGO",
            label=f"{ship.cargo_type} — ${float(ship.cargo_value_usd):,.0f}",
            detail=(
                f"+{lnk.delay_hours:.0f}h delay | "
                f"impact={lnk.impact_score:.2f} | "
                f"{'cold-chain' if ship.temperature_sensitive else 'ambient'}"
            ),
        )
        shipment_nodes.append(CascadeNodeSchema(
            level="SHIPMENTS",
            label=ship.shipment_code,
            detail=f"{ship.origin} → {ship.destination} | {ship.status.value if hasattr(ship.status, 'value') else ship.status}",
            children=[cargo_node],
        ))

    # Routes affected (unique via shipment routes)
    route_labels: set[str] = set()
    for lnk in links:
        ship = session.get(Shipment, lnk.shipment_id)
        if ship and ship.route_id:
            from app.models.route import Route
            rt = session.get(Route, ship.route_id)
            if rt:
                route_labels.add(f"{rt.route_code}: {rt.origin} → {rt.destination} ({rt.transport_mode})")

    route_nodes = [
        CascadeNodeSchema(level="ROUTES", label=lbl, children=shipment_nodes if i == 0 else [])
        for i, lbl in enumerate(sorted(route_labels))
    ]
    # If no route nodes, attach shipments directly
    if not route_nodes and shipment_nodes:
        route_nodes = [CascadeNodeSchema(
            level="ROUTES", label="(routes not yet assigned)", children=shipment_nodes
        )]

    port_node = CascadeNodeSchema(
        level="PORT_REGION",
        label=dis.affected_region,
        detail=f"Type: {type_str.upper()} | Severity: {dis.severity}/10",
        children=route_nodes,
    )

    root = CascadeNodeSchema(
        level="DISRUPTION",
        label=f"{dis.disruption_code} — {dis.name}",
        detail=dis.description[:120] + "..." if dis.description and len(dis.description) > 120 else dis.description,
        children=[port_node],
    )
    return root


def _dis_to_summary(session: Session, dis: Disruption) -> DisruptionSummary:
    n, cargo, avg_impact, delay, _temp = _aggregate_disruption(session, dis)
    type_str = dis.type.value if hasattr(dis.type, "value") else str(dis.type)
    status_str = dis.status.value if hasattr(dis.status, "value") else str(dis.status)
    return DisruptionSummary(
        id=dis.id,
        disruption_code=dis.disruption_code,
        name=dis.name,
        type=type_str,
        severity=dis.severity,
        affected_region=dis.affected_region,
        status=status_str,
        start_time=dis.start_time,
        end_time=dis.end_time,
        description=dis.description,
        affected_shipment_count=n,
        total_cargo_exposure_usd=cargo,
        avg_impact_score=avg_impact,
        total_delay_hours=delay,
        duration_hours=round(_duration_hours(dis), 2),
    )


def _dna_to_schema(dna) -> DNASchema:
    return DNASchema(
        disruption_id=dna.disruption_id,
        type_score=dna.type_score,
        type_label=dna.type_label,
        severity_score=dna.severity_score,
        severity_raw=dna.severity_raw,
        duration_score=dna.duration_score,
        duration_hours=dna.duration_hours,
        geo_scope_score=dna.geo_scope_score,
        geo_scope_label=dna.geo_scope_label,
        transport_mode_score=dna.transport_mode_score,
        transport_mode_label=dna.transport_mode_label,
        capacity_impact_score=dna.capacity_impact_score,
        port_relevance_score=dna.port_relevance_score,
        region_score=dna.region_score,
        region_label=dna.region_label,
        avg_impact_score=dna.avg_impact_score,
        affected_shipment_count=dna.affected_shipment_count,
        dna_summary=dna.dna_summary,
        generated_at=dna.generated_at,
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get(
    "",
    response_model=list[DisruptionSummary],
    summary="List all disruptions with aggregated impact statistics",
)
async def list_disruptions(
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> list[DisruptionSummary]:
    """
    Return all disruptions ordered by severity desc, start_time desc.
    Optionally filter by status (active / monitoring / historical / resolved).
    All aggregate values are computed from the database.
    """
    def _work(sync_session: Session) -> list[DisruptionSummary]:
        q = sync_session.query(Disruption).order_by(
            Disruption.severity.desc(),
            Disruption.start_time.desc(),
        )
        if status:
            try:
                status_enum = DisruptionStatus(status.lower())
                q = q.filter(Disruption.status == status_enum)
            except ValueError:
                pass  # ignore invalid status values
        disruptions = q.all()
        return [_dis_to_summary(sync_session, d) for d in disruptions]

    return await db.run_sync(_work)


@router.get(
    "/{disruption_id}",
    response_model=DisruptionDetailSchema,
    summary="Get full disruption detail including DNA",
)
async def get_disruption(
    disruption_id: int,
    db: AsyncSession = Depends(get_db),
) -> DisruptionDetailSchema:
    """Return full disruption detail. DNA is generated on demand if not cached."""
    def _work(sync_session: Session) -> DisruptionDetailSchema | None:
        dis = sync_session.get(Disruption, disruption_id)
        if dis is None:
            return None
        n, cargo, avg_impact, delay, temp_count = _aggregate_disruption(sync_session, dis)
        type_str = dis.type.value if hasattr(dis.type, "value") else str(dis.type)
        status_str = dis.status.value if hasattr(dis.status, "value") else str(dis.status)

        dna = generate_dna(sync_session, dis, cfg)
        sync_session.flush()

        return DisruptionDetailSchema(
            id=dis.id,
            disruption_code=dis.disruption_code,
            name=dis.name,
            type=type_str,
            severity=dis.severity,
            affected_region=dis.affected_region,
            status=status_str,
            start_time=dis.start_time,
            end_time=dis.end_time,
            description=dis.description,
            duration_hours=round(_duration_hours(dis), 2),
            affected_shipment_count=n,
            total_cargo_exposure_usd=cargo,
            avg_impact_score=avg_impact,
            total_delay_hours=delay,
            temperature_sensitive_count=temp_count,
            dna=_dna_to_schema(dna),
        )

    result = await db.run_sync(_work)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Disruption {disruption_id} not found")
    await db.commit()
    return result


@router.get(
    "/{disruption_id}/dna",
    response_model=DNASchema,
    summary="Get or generate Disruption DNA fingerprint",
)
async def get_disruption_dna(
    disruption_id: int,
    db: AsyncSession = Depends(get_db),
) -> DNASchema:
    """Generate and return the DNA fingerprint for a disruption."""
    def _work(sync_session: Session) -> DNASchema | None:
        dis = sync_session.get(Disruption, disruption_id)
        if dis is None:
            return None
        dna = generate_dna(sync_session, dis, cfg)
        sync_session.flush()
        return _dna_to_schema(dna)

    result = await db.run_sync(_work)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Disruption {disruption_id} not found")
    await db.commit()
    return result


@router.get(
    "/{disruption_id}/similar",
    response_model=list[SimilarityResultSchema],
    summary="Find similar historical disruptions using Disruption DNA",
)
async def get_similar_disruptions(
    disruption_id: int,
    db: AsyncSession = Depends(get_db),
) -> list[SimilarityResultSchema]:
    """
    Compare subject disruption DNA against historical disruptions.
    Returns top similar disruptions with weighted feature breakdown.
    All scores are deterministic — no LLM.
    """
    def _work(sync_session: Session) -> list[SimilarityResultSchema] | None:
        dis = sync_session.get(Disruption, disruption_id)
        if dis is None:
            return None
        results = find_similar_disruptions(sync_session, dis, cfg)
        sync_session.flush()
        out: list[SimilarityResultSchema] = []
        for r in results:
            dim_matches = [
                DimensionMatchSchema(
                    dimension=m.dimension,
                    weight=m.weight,
                    subject_score=m.subject_score,
                    candidate_score=m.candidate_score,
                    difference=m.difference,
                    contribution=m.contribution,
                    match_quality=m.match_quality,
                )
                for m in r.dimension_matches
            ]
            out.append(SimilarityResultSchema(
                disruption_id=r.disruption_id,
                disruption_code=r.disruption_code,
                name=r.name,
                disruption_type=r.disruption_type,
                severity=r.severity,
                affected_region=r.affected_region,
                status=r.status,
                duration_hours=r.duration_hours,
                similarity_score=r.similarity_score,
                dimension_matches=dim_matches,
                top_matching_dimensions=r.top_matching_dimensions,
                historical_outcome=r.historical_outcome,
            ))
        return out

    result = await db.run_sync(_work)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Disruption {disruption_id} not found")
    await db.commit()
    return result


@router.get(
    "/{disruption_id}/impact",
    response_model=DisruptionImpactSchema,
    summary="Get full cascading impact view for a disruption",
)
async def get_disruption_impact(
    disruption_id: int,
    db: AsyncSession = Depends(get_db),
) -> DisruptionImpactSchema:
    """
    Return full cascading impact: disruption → port/region → routes → shipments → cargo.
    All relationships are real database relationships.
    """
    def _work(sync_session: Session) -> DisruptionImpactSchema | None:
        dis = sync_session.get(Disruption, disruption_id)
        if dis is None:
            return None

        links: list[ShipmentDisruption] = (
            sync_session.query(ShipmentDisruption)
            .filter(ShipmentDisruption.disruption_id == disruption_id)
            .all()
        )

        affected: list[ShipmentImpactSchema] = []
        total_cargo = 0.0
        total_delay = 0.0
        total_impact = 0.0
        temp_count = 0

        for lnk in links:
            ship: Shipment | None = sync_session.get(Shipment, lnk.shipment_id)
            if ship is None:
                continue
            cargo_val = float(ship.cargo_value_usd)
            total_cargo += cargo_val
            total_delay += lnk.delay_hours
            total_impact += lnk.impact_score
            if ship.temperature_sensitive:
                temp_count += 1
            priority_str = ship.priority.value if hasattr(ship.priority, "value") else str(ship.priority)
            status_str = ship.status.value if hasattr(ship.status, "value") else str(ship.status)
            affected.append(ShipmentImpactSchema(
                shipment_id=ship.id,
                shipment_code=ship.shipment_code,
                origin=ship.origin,
                destination=ship.destination,
                cargo_type=ship.cargo_type,
                cargo_value_usd=cargo_val,
                weight_kg=ship.weight_kg,
                priority=priority_str,
                status=status_str,
                temperature_sensitive=ship.temperature_sensitive,
                impact_score=lnk.impact_score,
                delay_hours=lnk.delay_hours,
            ))

        n = len(affected)
        avg_impact = round(total_impact / n, 4) if n else 0.0
        cascade = _build_cascade(sync_session, dis)

        type_str = dis.type.value if hasattr(dis.type, "value") else str(dis.type)
        return DisruptionImpactSchema(
            disruption_id=dis.id,
            disruption_code=dis.disruption_code,
            name=dis.name,
            affected_shipments=affected,
            total_cargo_exposure_usd=round(total_cargo, 2),
            affected_shipment_count=n,
            temperature_sensitive_count=temp_count,
            total_delay_hours=round(total_delay, 2),
            avg_impact_score=avg_impact,
            cascade=cascade,
        )

    result = await db.run_sync(_work)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Disruption {disruption_id} not found")
    return result


# ── AI Decision Support endpoint ──────────────────────────────────────────────

@router.get(
    "/{disruption_id}/ai-insights",
    response_model=None,  # Dynamic schema based on watsonx availability
    summary="AI Decision Support panel data",
    tags=["AI"],
)
async def get_disruption_ai_insights(
    disruption_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Return pre-calculated system facts AND optional IBM watsonx.ai insights
    for the disruption. This is the AI Decision Support panel data endpoint.

    SYSTEM FACTS (always present):
      - All values are calculated by deterministic Python services.
      - These values are the same as those returned by /api/disruptions/{id},
        /api/disruptions/{id}/dna, /api/disruptions/{id}/similar, and
        /api/disruptions/{id}/impact.
      - They are included here in a single call for the AI panel.

    AI INSIGHTS (present only when watsonx is configured):
      - Generated by IBM watsonx.ai from the system facts above.
      - Clearly labelled as AI-generated text.
      - AI failure does not affect this endpoint's ability to return system facts.
      - When watsonx is not configured, status='unavailable' and insights=null.

    Required environment variables to enable AI:
      WATSONX_API_KEY      — IBM Cloud API key
      WATSONX_PROJECT_ID   — watsonx.ai project ID
      WATSONX_URL          — regional endpoint (default: https://us-south.ml.cloud.ibm.com)
    """
    from app.services.watsonx_service import (
        SystemFacts,
        get_watsonx_service_or_none,
        make_unavailable_response,
        _facts_to_dict,
    )
    from app.schemas.ai_insights import AIInsightsResponseSchema
    from app.core.config import get_settings

    settings = get_settings()

    def _work(sync_session: Session):
        dis = sync_session.get(Disruption, disruption_id)
        if dis is None:
            return None

        # ── Aggregate disruption facts ────────────────────────────────────
        n, cargo, avg_impact, delay, temp_count = _aggregate_disruption(sync_session, dis)
        duration_h = round(_duration_hours(dis), 2)
        type_str = dis.type.value if hasattr(dis.type, "value") else str(dis.type)
        status_str = dis.status.value if hasattr(dis.status, "value") else str(dis.status)

        # ── DNA facts ─────────────────────────────────────────────────────
        dna = generate_dna(sync_session, dis, cfg)
        sync_session.flush()

        # ── Similarity facts ──────────────────────────────────────────────
        similar = find_similar_disruptions(sync_session, dis, cfg)
        sync_session.flush()
        top_similar = similar[0] if similar else None

        # ── Priority shipment facts ───────────────────────────────────────
        # Load the affected shipments to find priority shipment (S-1042 or highest impact)
        links: list[ShipmentDisruption] = (
            sync_session.query(ShipmentDisruption)
            .filter(ShipmentDisruption.disruption_id == dis.id)
            .all()
        )

        priority_ship = None
        priority_link = None
        if links:
            # Prefer S-1042 (demo shipment), else highest impact score
            for lnk in links:
                ship = sync_session.get(Shipment, lnk.shipment_id)
                if ship and ship.shipment_code == "S-1042":
                    priority_ship = ship
                    priority_link = lnk
                    break
            if priority_ship is None:
                best = max(links, key=lambda lnk: lnk.impact_score)
                priority_ship = sync_session.get(Shipment, best.shipment_id)
                priority_link = best

        # ── Wallet/RRI facts for priority shipment ────────────────────────
        p_rri: float | None = None
        p_rri_status: str | None = None
        most_depleted_dim: str | None = None
        most_depleted_score: float | None = None

        if priority_ship is not None:
            from app.models.route import Route
            from app.services.wallet_service import get_wallet_state
            from app.services.rri_calculator import calculate_rri
            from app.services.resilience_config import DEFAULT_CONFIG

            if priority_ship.route_id:
                priority_ship.route = sync_session.get(Route, priority_ship.route_id)

            try:
                ws = get_wallet_state(sync_session, priority_ship, DEFAULT_CONFIG)
                exp = calculate_rri(ws, priority_ship.priority, DEFAULT_CONFIG)
                p_rri = exp.rri
                p_rri_status = exp.status.value

                # Most depleted = lowest remaining score
                dims = [
                    ("time", ws.time.dimension_score),
                    ("cost", ws.cost.dimension_score),
                    ("temperature", ws.temperature.dimension_score),
                    ("capacity", ws.capacity.dimension_score),
                ]
                most_depleted = min(dims, key=lambda x: x[1])
                most_depleted_dim = most_depleted[0]
                most_depleted_score = most_depleted[1]
            except Exception:  # pylint: disable=broad-except
                pass  # Wallet unavailable — still return other facts

        # ── Assemble SystemFacts ──────────────────────────────────────────
        facts = SystemFacts(
            disruption_code=dis.disruption_code,
            disruption_name=dis.name,
            disruption_type=type_str,
            severity=dis.severity,
            affected_region=dis.affected_region,
            status=status_str,
            duration_hours=duration_h,
            affected_shipment_count=n,
            total_cargo_exposure_usd=cargo,
            total_delay_hours=delay,
            dna_summary=dna.dna_summary,
            geo_scope_label=dna.geo_scope_label,
            transport_mode_label=dna.transport_mode_label,
            port_relevance_score=dna.port_relevance_score,
            capacity_impact_score=dna.capacity_impact_score,
            top_similar_disruption_name=top_similar.name if top_similar else None,
            top_similar_score=top_similar.similarity_score if top_similar else None,
            priority_shipment_code=priority_ship.shipment_code if priority_ship else None,
            priority_shipment_rri=p_rri,
            priority_shipment_rri_status=p_rri_status,
            priority_shipment_cargo_usd=(
                float(priority_ship.cargo_value_usd) if priority_ship else None
            ),
            priority_shipment_impact_score=priority_link.impact_score if priority_link else None,
            priority_shipment_delay_hours=priority_link.delay_hours if priority_link else None,
            priority_shipment_is_cold_chain=(
                priority_ship.temperature_sensitive if priority_ship else False
            ),
            most_depleted_dimension=most_depleted_dim,
            most_depleted_score=most_depleted_score,
        )
        return facts

    result = await db.run_sync(_work)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Disruption {disruption_id} not found")

    await db.commit()
    facts = result
    facts_dict = _facts_to_dict(facts)

    # ── Try watsonx; fall back gracefully ─────────────────────────────────
    service = get_watsonx_service_or_none(
        api_key=settings.watsonx_api_key,
        project_id=settings.watsonx_project_id,
        url=settings.watsonx_url,
    )

    if service is None:
        response_data = make_unavailable_response(facts_dict)
    else:
        response_data = service.generate_insights(facts)
        # Ensure facts_dict is always the deterministic version
        response_data.system_facts = facts_dict

    return AIInsightsResponseSchema(
        watsonx_enabled=response_data.watsonx_enabled,
        status=response_data.status,
        message=response_data.message,
        system_facts=response_data.system_facts,
        insights=(
            {
                "disruption_explanation": response_data.insights.disruption_explanation,
                "risk_summary": response_data.insights.risk_summary,
                "decision_support": response_data.insights.decision_support,
                "recommended_actions": response_data.insights.recommended_actions,
                "model_id": response_data.insights.model_id,
                "tokens_used": response_data.insights.tokens_used,
            }
            if response_data.insights
            else None
        ),
        error_detail=response_data.error_detail,
    )
