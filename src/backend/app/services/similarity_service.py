"""SupplyShield Disruption Similarity Service.

Computes deterministic similarity scores between disruptions
using a weighted feature-vector comparison on Disruption DNA.

Algorithm:
  1. Generate DNA for subject and each historical disruption.
  2. For each DNA dimension, compute absolute difference: diff = |a - b|
     → similarity contribution = (1 - diff) * weight
  3. Total score = sum(contributions) * 100  → [0, 100]
  4. Filter by minimum threshold, sort descending, return top-N.

No machine learning is used. All weights are configurable
SupplyShield model assumptions documented in dna_config.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.models.disruption import Disruption, DisruptionStatus
from app.models.disruption_dna import DisruptionDNA
from app.services.dna_config import DNAConfig, DEFAULT_DNA_CONFIG
from app.services.dna_service import generate_dna


@dataclass
class DimensionMatch:
    """Contribution of a single DNA dimension to the similarity score."""
    dimension: str
    weight: float
    subject_score: float
    candidate_score: float
    difference: float
    contribution: float    # contribution to overall similarity [0, weight]
    match_quality: str     # STRONG / MODERATE / WEAK / NONE


@dataclass
class SimilarityResult:
    """Result of comparing two disruptions."""
    disruption_id: int
    disruption_code: str
    name: str
    disruption_type: str
    severity: int
    affected_region: str
    status: str
    duration_hours: float
    similarity_score: float          # 0–100
    dimension_matches: list[DimensionMatch] = field(default_factory=list)
    top_matching_dimensions: list[str] = field(default_factory=list)
    # Historical recovery data (if any recorded in description)
    historical_outcome: str | None = None


def _match_quality(contribution: float, weight: float) -> str:
    if weight == 0:
        return "NONE"
    ratio = contribution / weight  # 0–1
    if ratio >= 0.85:
        return "STRONG"
    if ratio >= 0.60:
        return "MODERATE"
    if ratio >= 0.35:
        return "WEAK"
    return "NONE"


def _compute_dimension_matches(
    subject_dna: DisruptionDNA,
    candidate_dna: DisruptionDNA,
    weights: dict[str, float],
) -> tuple[float, list[DimensionMatch]]:
    """
    Compute weighted similarity between two DNA records.
    Returns (total_score_0_100, dimension_matches).
    """
    dimensions: list[tuple[str, float, float]] = [
        ("type",      subject_dna.type_score,           candidate_dna.type_score),
        ("severity",  subject_dna.severity_score,       candidate_dna.severity_score),
        ("region",    subject_dna.region_score,         candidate_dna.region_score),
        ("duration",  subject_dna.duration_score,       candidate_dna.duration_score),
        ("geo_scope", subject_dna.geo_scope_score,      candidate_dna.geo_scope_score),
        ("transport", subject_dna.transport_mode_score, candidate_dna.transport_mode_score),
        ("capacity",  subject_dna.capacity_impact_score,candidate_dna.capacity_impact_score),
    ]

    total_contribution = 0.0
    matches: list[DimensionMatch] = []

    for dim_name, s_val, c_val in dimensions:
        w = weights.get(dim_name, 0.0)
        diff = abs(s_val - c_val)           # 0 = identical, 1 = maximally different
        contribution = (1.0 - diff) * w     # higher = more similar
        total_contribution += contribution
        matches.append(DimensionMatch(
            dimension=dim_name,
            weight=w,
            subject_score=round(s_val, 4),
            candidate_score=round(c_val, 4),
            difference=round(diff, 4),
            contribution=round(contribution, 4),
            match_quality=_match_quality(contribution, w),
        ))

    # total_contribution is in [0, 1] (weights sum to 1.0)
    return round(total_contribution * 100.0, 2), matches


def _extract_historical_outcome(disruption: Disruption) -> str | None:
    """
    Extract outcome text from disruption description if it contains
    retrospective language. Only returns text that exists in the DB.
    """
    if not disruption.description:
        return None
    desc = disruption.description

    # Historical disruptions may contain outcome keywords
    outcome_keywords = [
        "historical reference", "resolved", "recovery", "outcome",
        "restored", "reopened", "cleared", "lifted", "returned"
    ]
    if any(kw in desc.lower() for kw in outcome_keywords):
        return desc
    return None


def find_similar_disruptions(
    session: Session,
    subject: Disruption,
    cfg: DNAConfig | None = None,
    exclude_status: list[str] | None = None,
) -> list[SimilarityResult]:
    """
    Find historical/monitoring disruptions most similar to `subject`.

    Steps:
    1. Generate DNA for subject.
    2. Fetch all candidate disruptions (excluding subject + active by default).
    3. Generate DNA for each candidate.
    4. Compute weighted similarity score.
    5. Filter by threshold, sort desc, return top-N.

    Returns list of SimilarityResult, sorted by similarity_score descending.
    """
    if cfg is None:
        cfg = DEFAULT_DNA_CONFIG

    if exclude_status is None:
        # Exclude ACTIVE — compare against HISTORICAL and MONITORING only
        exclude_status = ["active"]

    weights = cfg.weights.as_dict()
    subject_dna = generate_dna(session, subject, cfg)

    # Fetch candidates
    q = session.query(Disruption).filter(Disruption.id != subject.id)
    if exclude_status:
        from app.models.disruption import DisruptionStatus as DS
        excluded = [DS(s) for s in exclude_status if s in DS._value2member_map_]
        if excluded:
            q = q.filter(~Disruption.status.in_(excluded))
    candidates: list[Disruption] = q.all()

    results: list[SimilarityResult] = []

    for cand in candidates:
        cand_dna = generate_dna(session, cand, cfg)
        score, dim_matches = _compute_dimension_matches(subject_dna, cand_dna, weights)

        if score < cfg.min_similarity_threshold:
            continue

        # Top-matching dimensions (STRONG or MODERATE quality)
        top_dims = [
            m.dimension for m in sorted(dim_matches, key=lambda x: x.contribution, reverse=True)
            if m.match_quality in ("STRONG", "MODERATE")
        ]

        cand_status = cand.status.value if hasattr(cand.status, "value") else str(cand.status)
        cand_type = cand.type.value if hasattr(cand.type, "value") else str(cand.type)

        results.append(SimilarityResult(
            disruption_id=cand.id,
            disruption_code=cand.disruption_code,
            name=cand.name,
            disruption_type=cand_type,
            severity=cand.severity,
            affected_region=cand.affected_region,
            status=cand_status,
            duration_hours=cand_dna.duration_hours,
            similarity_score=score,
            dimension_matches=dim_matches,
            top_matching_dimensions=top_dims[:3],
            historical_outcome=_extract_historical_outcome(cand),
        ))

    # Sort by similarity descending, take top-N
    results.sort(key=lambda r: r.similarity_score, reverse=True)
    return results[: cfg.max_similar_results]
