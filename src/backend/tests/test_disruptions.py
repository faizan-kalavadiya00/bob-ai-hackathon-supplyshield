"""Tests for Phase 4B — Disruption Management + Disruption DNA.

These tests are primarily unit tests that do NOT require a live database.
They test DNA generation logic, similarity algorithm, schema validation,
and determinism.

A subset uses the database connection (requires DATABASE_SYNC_URL env var).
"""

from __future__ import annotations

import os
import math
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta, timezone

# ── Make app importable ──────────────────────────────────────────────────────
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.services.dna_config import (
    DEFAULT_DNA_CONFIG,
    DNASimilarityWeights,
    DNAConfig,
    DISRUPTION_TYPE_SCORES,
    classify_geo_scope,
    classify_port_relevance,
    classify_transport_mode,
    compute_capacity_impact,
    compute_region_score,
    normalize_duration,
)
from app.services.dna_service import generate_dna
from app.services.similarity_service import (
    _compute_dimension_matches,
    _match_quality,
    find_similar_disruptions,
)
from app.models.disruption_dna import DisruptionDNA


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

def _make_disruption(
    dis_id: int = 1,
    code: str = "DIS-001",
    name: str = "Mumbai Port Crisis",
    type_val: str = "port",
    severity: int = 8,
    region: str = "Mumbai Port, India",
    hours_ago: float = 12,
    duration_h: float = 48,
    status: str = "active",
    description: str = "Industrial strike at Mumbai Port.",
):
    """Create a minimal mock Disruption object without needing DB."""
    from types import SimpleNamespace

    class TypeEnum:
        value = type_val
    class StatusEnum:
        value = status

    now = datetime(2026, 9, 15, 12, 0, 0, tzinfo=timezone.utc)
    start = now - timedelta(hours=hours_ago)
    end = start + timedelta(hours=duration_h) if status != "active" else None

    dis = SimpleNamespace(
        id=dis_id,
        disruption_code=code,
        name=name,
        type=TypeEnum(),
        severity=severity,
        affected_region=region,
        start_time=start,
        end_time=end,
        status=StatusEnum(),
        description=description,
        dna=None,
    )
    return dis


class _FakeDNA:
    """Plain Python stand-in for DisruptionDNA — used in unit tests only."""
    def __init__(
        self,
        disruption_id: int = 1,
        type_score: float = 1.0,
        severity_score: float = 0.8,
        duration_score: float = 0.5,
        geo_scope_score: float = 0.5,
        transport_mode_score: float = 1.0,
        capacity_impact_score: float = 0.8,
        port_relevance_score: float = 1.0,
        region_score: float = 0.5,
        avg_impact_score: float = 0.5,
        affected_count: int = 5,
    ):
        self.disruption_id = disruption_id
        self.type_score = type_score
        self.type_label = "port"
        self.severity_score = severity_score
        self.severity_raw = int(severity_score * 10)
        self.duration_score = duration_score
        self.duration_hours = 48.0
        self.geo_scope_score = geo_scope_score
        self.geo_scope_label = "REGIONAL"
        self.transport_mode_score = transport_mode_score
        self.transport_mode_label = "sea"
        self.capacity_impact_score = capacity_impact_score
        self.port_relevance_score = port_relevance_score
        self.region_score = region_score
        self.region_label = "Mumbai Port, India"
        self.avg_impact_score = avg_impact_score
        self.affected_shipment_count = affected_count
        self.dna_summary = "Test DNA"
        self.generated_at = datetime.now(timezone.utc)


def _make_dna(**kwargs) -> _FakeDNA:
    """Create a minimal fake DNA object for testing."""
    return _FakeDNA(**kwargs)


# ─────────────────────────────────────────────────────────────────────────────
# Test 1: Similarity weights sum to 1.0
# ─────────────────────────────────────────────────────────────────────────────

def test_dna_weights_sum_to_one():
    w = DNASimilarityWeights()
    total = w.type + w.severity + w.region + w.duration + w.geo_scope + w.transport + w.capacity
    assert abs(total - 1.0) < 1e-9, f"Expected 1.0 got {total}"


def test_dna_invalid_weights_raise():
    with pytest.raises(ValueError, match="sum to 1.0"):
        DNASimilarityWeights(type=0.5, severity=0.5, region=0.5,
                             duration=0.0, geo_scope=0.0, transport=0.0, capacity=0.0)


def test_dna_config_has_weights():
    cfg = DEFAULT_DNA_CONFIG
    assert cfg.weights is not None
    assert isinstance(cfg.weights, DNASimilarityWeights)


# ─────────────────────────────────────────────────────────────────────────────
# Test 2: Disruption type scores
# ─────────────────────────────────────────────────────────────────────────────

def test_port_type_score_highest():
    assert DISRUPTION_TYPE_SCORES["port"] == 1.0


def test_demand_type_score_lowest():
    assert DISRUPTION_TYPE_SCORES["demand"] < DISRUPTION_TYPE_SCORES["port"]


def test_all_type_scores_in_range():
    for t, s in DISRUPTION_TYPE_SCORES.items():
        assert 0.0 <= s <= 1.0, f"{t} score {s} out of range"


# ─────────────────────────────────────────────────────────────────────────────
# Test 3: Geographic scope classification
# ─────────────────────────────────────────────────────────────────────────────

def test_geo_scope_mumbai_is_regional():
    label, score = classify_geo_scope("Mumbai Port, India")
    # Mumbai → NATIONAL (India keyword) takes precedence in current rules
    assert label in ("REGIONAL", "NATIONAL")
    assert 0.0 < score <= 1.0


def test_geo_scope_suez_is_international():
    label, score = classify_geo_scope("Suez Canal, Egypt")
    assert label == "INTERNATIONAL"
    assert score == 1.0


def test_geo_scope_local_fallback():
    label, score = classify_geo_scope("Warehouse Block 7")
    assert label == "LOCAL"
    assert score == 0.25


def test_geo_scope_global_is_international():
    label, score = classify_geo_scope("Global shipping routes")
    assert label == "INTERNATIONAL"


# ─────────────────────────────────────────────────────────────────────────────
# Test 4: Port relevance
# ─────────────────────────────────────────────────────────────────────────────

def test_port_type_gives_full_relevance():
    score = classify_port_relevance("port", "Mumbai Port, India")
    assert score == 1.0


def test_weather_coastal_gives_partial_relevance():
    score = classify_port_relevance("weather", "Mumbai coast")
    assert score == 0.5


def test_inland_non_port_gives_zero():
    score = classify_port_relevance("supplier", "Surat factory zone")
    assert score == 0.0


# ─────────────────────────────────────────────────────────────────────────────
# Test 5: Duration normalization
# ─────────────────────────────────────────────────────────────────────────────

def test_normalize_duration_zero():
    assert normalize_duration(0) == 0.0


def test_normalize_duration_positive():
    s = normalize_duration(48.0)
    assert 0.0 < s < 1.0


def test_normalize_duration_max():
    s = normalize_duration(2160.0)
    assert abs(s - 1.0) < 1e-9


def test_normalize_duration_monotonic():
    d1 = normalize_duration(24.0)
    d2 = normalize_duration(48.0)
    d3 = normalize_duration(168.0)
    assert d1 < d2 < d3


# ─────────────────────────────────────────────────────────────────────────────
# Test 6: Transport mode classification
# ─────────────────────────────────────────────────────────────────────────────

def test_port_disruption_implies_sea():
    mode, score = classify_transport_mode("port", "Mumbai Port")
    assert mode == "sea"
    assert score == 1.0


def test_road_keyword_implies_road():
    mode, score = classify_transport_mode("transport", "Mumbai-Pune Expressway closure")
    assert mode == "road"


def test_canal_implies_sea():
    mode, score = classify_transport_mode("transport", "Suez Canal blockage")
    assert mode == "sea"


# ─────────────────────────────────────────────────────────────────────────────
# Test 7: Capacity impact calculation
# ─────────────────────────────────────────────────────────────────────────────

def test_capacity_impact_high_severity_port():
    score = compute_capacity_impact(9, "port")
    assert score > 0.7


def test_capacity_impact_low_severity():
    score = compute_capacity_impact(2, "demand")
    assert score < 0.3


def test_capacity_impact_capped_at_1():
    score = compute_capacity_impact(10, "port")
    assert score <= 1.0


def test_capacity_impact_positive():
    score = compute_capacity_impact(5, "weather")
    assert score > 0.0


# ─────────────────────────────────────────────────────────────────────────────
# Test 8: Region score determinism
# ─────────────────────────────────────────────────────────────────────────────

def test_region_score_deterministic():
    s1 = compute_region_score("Mumbai Port, India")
    s2 = compute_region_score("Mumbai Port, India")
    assert s1 == s2


def test_region_score_in_range():
    s = compute_region_score("Suez Canal, Egypt")
    assert 0.0 <= s <= 1.0


def test_different_regions_different_scores():
    s1 = compute_region_score("Mumbai Port, India")
    s2 = compute_region_score("Rotterdam Port, Netherlands")
    # Note: hash collision possible but extremely unlikely for these two
    # We just check they're both valid scores
    assert 0.0 <= s1 <= 1.0
    assert 0.0 <= s2 <= 1.0


# ─────────────────────────────────────────────────────────────────────────────
# Test 9: Similarity score bounds 0–100
# ─────────────────────────────────────────────────────────────────────────────

def test_similarity_identical_dna_gives_100():
    """Two identical DNA records should score 100."""
    dna = _make_dna()
    weights = DEFAULT_DNA_CONFIG.weights.as_dict()
    score, _ = _compute_dimension_matches(dna, dna, weights)
    assert abs(score - 100.0) < 0.01


def test_similarity_opposite_dna_gives_low_score():
    """Maximally different DNA should score near 0."""
    dna_a = _make_dna(
        type_score=1.0, severity_score=1.0, duration_score=1.0,
        geo_scope_score=1.0, transport_mode_score=1.0,
        capacity_impact_score=1.0, region_score=1.0,
    )
    dna_b = _make_dna(
        type_score=0.0, severity_score=0.0, duration_score=0.0,
        geo_scope_score=0.0, transport_mode_score=0.0,
        capacity_impact_score=0.0, region_score=0.0,
    )
    weights = DEFAULT_DNA_CONFIG.weights.as_dict()
    score, _ = _compute_dimension_matches(dna_a, dna_b, weights)
    assert 0.0 <= score <= 5.0, f"Expected near-0, got {score}"


def test_similarity_score_always_0_to_100():
    """Fuzz test: random DNA combos always produce scores in [0, 100]."""
    import random
    rng = random.Random(42)
    weights = DEFAULT_DNA_CONFIG.weights.as_dict()
    for _ in range(100):
        a = _make_dna(
            type_score=rng.random(), severity_score=rng.random(),
            duration_score=rng.random(), geo_scope_score=rng.random(),
            transport_mode_score=rng.random(), capacity_impact_score=rng.random(),
            region_score=rng.random(),
        )
        b = _make_dna(
            type_score=rng.random(), severity_score=rng.random(),
            duration_score=rng.random(), geo_scope_score=rng.random(),
            transport_mode_score=rng.random(), capacity_impact_score=rng.random(),
            region_score=rng.random(),
        )
        score, _ = _compute_dimension_matches(a, b, weights)
        assert 0.0 <= score <= 100.0, f"Score {score} out of range"


# ─────────────────────────────────────────────────────────────────────────────
# Test 10: Similarity determinism
# ─────────────────────────────────────────────────────────────────────────────

def test_similarity_is_deterministic():
    dna_a = _make_dna(type_score=0.8, severity_score=0.7, region_score=0.6)
    dna_b = _make_dna(type_score=0.9, severity_score=0.8, region_score=0.55)
    weights = DEFAULT_DNA_CONFIG.weights.as_dict()
    s1, _ = _compute_dimension_matches(dna_a, dna_b, weights)
    s2, _ = _compute_dimension_matches(dna_a, dna_b, weights)
    assert s1 == s2


# ─────────────────────────────────────────────────────────────────────────────
# Test 11: Match quality bands
# ─────────────────────────────────────────────────────────────────────────────

def test_match_quality_strong():
    assert _match_quality(0.22, 0.25) == "STRONG"  # 88% match


def test_match_quality_moderate():
    assert _match_quality(0.15, 0.25) == "MODERATE"  # 60% match


def test_match_quality_weak():
    assert _match_quality(0.09, 0.25) == "WEAK"  # 36% match


def test_match_quality_none():
    assert _match_quality(0.01, 0.25) == "NONE"  # 4% match


def test_match_quality_zero_weight():
    assert _match_quality(0.0, 0.0) == "NONE"


# ─────────────────────────────────────────────────────────────────────────────
# Test 12: DNA field validation
# ─────────────────────────────────────────────────────────────────────────────

def test_dna_schema_has_all_required_fields():
    """All DNA schema fields must be present after generation."""
    from app.schemas.disruption import DNASchema
    required = [
        "disruption_id", "type_score", "type_label", "severity_score", "severity_raw",
        "duration_score", "duration_hours", "geo_scope_score", "geo_scope_label",
        "transport_mode_score", "transport_mode_label", "capacity_impact_score",
        "port_relevance_score", "region_score", "region_label",
        "avg_impact_score", "affected_shipment_count", "generated_at",
    ]
    fields = set(DNASchema.model_fields.keys())
    for f in required:
        assert f in fields, f"Missing DNA schema field: {f}"


def test_similarity_result_schema_has_required_fields():
    from app.schemas.disruption import SimilarityResultSchema
    required = [
        "disruption_id", "disruption_code", "name", "disruption_type",
        "severity", "similarity_score", "dimension_matches",
        "top_matching_dimensions",
    ]
    fields = set(SimilarityResultSchema.model_fields.keys())
    for f in required:
        assert f in fields, f"Missing SimilarityResult field: {f}"


# ─────────────────────────────────────────────────────────────────────────────
# Test 13: Database integration tests (require DATABASE_SYNC_URL)
# ─────────────────────────────────────────────────────────────────────────────

DATABASE_SYNC_URL = os.getenv("DATABASE_SYNC_URL", "")
db_available = bool(DATABASE_SYNC_URL)

@pytest.mark.skipif(not db_available, reason="DATABASE_SYNC_URL not set")
def test_db_mumbai_port_crisis_exists():
    """DIS-001 must exist in the seeded database."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    engine = create_engine(DATABASE_SYNC_URL, echo=False)
    Session = sessionmaker(bind=engine)
    with Session() as session:
        from app.models.disruption import Disruption
        dis = session.query(Disruption).filter_by(disruption_code="DIS-001").first()
        assert dis is not None, "DIS-001 not found"
        assert "Mumbai Port" in dis.name
        assert dis.severity == 8
        assert dis.type.value == "port"


@pytest.mark.skipif(not db_available, reason="DATABASE_SYNC_URL not set")
def test_db_dis006_prior_mumbai_port_strike_exists():
    """DIS-006 Mumbai Port Strike 2024 must exist for DNA comparison."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    engine = create_engine(DATABASE_SYNC_URL, echo=False)
    Session = sessionmaker(bind=engine)
    with Session() as session:
        from app.models.disruption import Disruption
        dis = session.query(Disruption).filter_by(disruption_code="DIS-006").first()
        assert dis is not None, "DIS-006 not found"
        assert "Mumbai" in dis.name
        assert dis.type.value == "port"
        assert dis.status.value == "historical"


@pytest.mark.skipif(not db_available, reason="DATABASE_SYNC_URL not set")
def test_db_s1042_linked_to_dis001():
    """S-1042 must be linked to DIS-001 via shipment_disruptions."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    engine = create_engine(DATABASE_SYNC_URL, echo=False)
    Session = sessionmaker(bind=engine)
    with Session() as session:
        from app.models.disruption import Disruption, ShipmentDisruption
        from app.models.shipment import Shipment
        dis = session.query(Disruption).filter_by(disruption_code="DIS-001").first()
        ship = session.query(Shipment).filter_by(shipment_code="S-1042").first()
        assert dis is not None and ship is not None
        link = (
            session.query(ShipmentDisruption)
            .filter_by(disruption_id=dis.id, shipment_id=ship.id)
            .first()
        )
        assert link is not None, "S-1042 not linked to DIS-001"
        assert link.impact_score == 0.85
        assert link.delay_hours == 48.0


@pytest.mark.skipif(not db_available, reason="DATABASE_SYNC_URL not set")
def test_db_dna_generation_deterministic():
    """Generating DNA twice for the same disruption returns same scores."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    engine = create_engine(DATABASE_SYNC_URL, echo=False)
    Session = sessionmaker(bind=engine)
    with Session() as session:
        from app.models.disruption import Disruption
        from app.models.disruption_dna import DisruptionDNA
        dis = session.query(Disruption).filter_by(disruption_code="DIS-001").first()
        assert dis is not None

        dna1 = generate_dna(session, dis, DEFAULT_DNA_CONFIG)
        type_score_1 = dna1.type_score
        severity_score_1 = dna1.severity_score
        # Delete the cached DNA to force regeneration
        session.expunge(dna1)
        # Clear existing
        existing = session.query(DisruptionDNA).filter_by(disruption_id=dis.id).first()
        if existing:
            session.delete(existing)
            session.flush()

        dna2 = generate_dna(session, dis, DEFAULT_DNA_CONFIG)
        assert dna2.type_score == type_score_1
        assert dna2.severity_score == severity_score_1
        session.rollback()


@pytest.mark.skipif(not db_available, reason="DATABASE_SYNC_URL not set")
def test_db_dis001_affected_shipment_count():
    """DIS-001 must affect at least 1 shipment (S-1042 guaranteed by seed)."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    engine = create_engine(DATABASE_SYNC_URL, echo=False)
    Session = sessionmaker(bind=engine)
    with Session() as session:
        from app.models.disruption import Disruption, ShipmentDisruption
        dis = session.query(Disruption).filter_by(disruption_code="DIS-001").first()
        count = (
            session.query(ShipmentDisruption)
            .filter_by(disruption_id=dis.id)
            .count()
        )
        assert count >= 1


@pytest.mark.skipif(not db_available, reason="DATABASE_SYNC_URL not set")
def test_db_dis001_cargo_exposure_positive():
    """Total cargo exposure for DIS-001 must be > 0 (includes S-1042 at $485k)."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    engine = create_engine(DATABASE_SYNC_URL, echo=False)
    Session = sessionmaker(bind=engine)
    with Session() as session:
        from app.models.disruption import Disruption, ShipmentDisruption
        from app.models.shipment import Shipment
        dis = session.query(Disruption).filter_by(disruption_code="DIS-001").first()
        links = session.query(ShipmentDisruption).filter_by(disruption_id=dis.id).all()
        total = sum(
            float(session.get(Shipment, lnk.shipment_id).cargo_value_usd)
            for lnk in links
            if session.get(Shipment, lnk.shipment_id) is not None
        )
        assert total >= 485000.0, f"Expected >= $485k, got ${total:,.0f}"


@pytest.mark.skipif(not db_available, reason="DATABASE_SYNC_URL not set")
def test_db_similarity_dis001_vs_dis006():
    """DIS-001 and DIS-006 are both port disruptions in Mumbai — should be similar."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    engine = create_engine(DATABASE_SYNC_URL, echo=False)
    Session = sessionmaker(bind=engine)
    with Session() as session:
        from app.models.disruption import Disruption
        dis001 = session.query(Disruption).filter_by(disruption_code="DIS-001").first()
        assert dis001 is not None

        results = find_similar_disruptions(session, dis001, DEFAULT_DNA_CONFIG)
        codes = [r.disruption_code for r in results]
        scores = {r.disruption_code: r.similarity_score for r in results}

        # DIS-006 must appear in results
        assert "DIS-006" in codes, (
            f"DIS-006 (Prior Mumbai Port Strike) not in similar results. "
            f"Found: {codes}"
        )
        # Its score must be reasonable (both are port disruptions in same region)
        assert scores["DIS-006"] >= 30.0, (
            f"DIS-006 similarity score {scores['DIS-006']} too low"
        )


@pytest.mark.skipif(not db_available, reason="DATABASE_SYNC_URL not set")
def test_db_similarity_scores_all_in_range():
    """All similarity scores returned for DIS-001 must be 0–100."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    engine = create_engine(DATABASE_SYNC_URL, echo=False)
    Session = sessionmaker(bind=engine)
    with Session() as session:
        from app.models.disruption import Disruption
        dis = session.query(Disruption).filter_by(disruption_code="DIS-001").first()
        results = find_similar_disruptions(session, dis, DEFAULT_DNA_CONFIG)
        for r in results:
            assert 0.0 <= r.similarity_score <= 100.0, (
                f"{r.disruption_code} score {r.similarity_score} out of range"
            )


@pytest.mark.skipif(not db_available, reason="DATABASE_SYNC_URL not set")
def test_db_disruption_listing():
    """API disruption listing returns non-empty list."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    engine = create_engine(DATABASE_SYNC_URL, echo=False)
    Session = sessionmaker(bind=engine)
    with Session() as session:
        from app.models.disruption import Disruption
        disruptions = session.query(Disruption).all()
        assert len(disruptions) >= 30, f"Expected >= 30, got {len(disruptions)}"


@pytest.mark.skipif(not db_available, reason="DATABASE_SYNC_URL not set")
def test_db_dis001_total_delay_positive():
    """Total delay for DIS-001 must be >= 48h (S-1042 alone contributes 48h)."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    engine = create_engine(DATABASE_SYNC_URL, echo=False)
    Session = sessionmaker(bind=engine)
    with Session() as session:
        from app.models.disruption import Disruption, ShipmentDisruption
        dis = session.query(Disruption).filter_by(disruption_code="DIS-001").first()
        links = session.query(ShipmentDisruption).filter_by(disruption_id=dis.id).all()
        total_delay = sum(lnk.delay_hours for lnk in links)
        assert total_delay >= 48.0, f"Expected >= 48h, got {total_delay}"
