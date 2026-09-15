"""SupplyShield Disruption DNA Configuration.

All DNA feature weights and attribute definitions live here.
These are documented as "SupplyShield configurable DNA model assumptions."
They do not claim to be industry-standard values.
No machine learning is used — the algorithm is fully deterministic and
transparent.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field


# ── Type ordering for score normalization ─────────────────────────────────────
# Higher score = more operationally disruptive type (SupplyShield assumption)
DISRUPTION_TYPE_SCORES: dict[str, float] = {
    "port":           1.0,   # direct physical blocking of freight flow
    "transport":      0.85,  # infrastructure/transit disruption
    "weather":        0.80,  # environmental — hard to predict, wide area
    "geopolitical":   0.75,  # border/trade — long tail uncertainty
    "regulatory":     0.60,  # compliance — manageable with preparation
    "supplier":       0.55,  # single-node failure — can often substitute
    "cyber":          0.50,  # increasingly important but not primary in this model
    "demand":         0.30,  # demand-side — less direct operational impact
}

# ── Geographic scope classification ──────────────────────────────────────────
# Derived from the affected_region string via keyword matching
GEO_SCOPE_RULES: list[tuple[list[str], str, float]] = [
    # keywords → scope_label, score
    (["suez", "red sea", "cape of good hope", "global", "worldwide", "international"],
     "INTERNATIONAL", 1.00),
    (["india", "china", "europe", "asia", "south china sea", "arabian sea", "bay of bengal",
      "indian ocean", "eu ", "european union"],
     "NATIONAL",      0.75),
    (["mumbai", "chennai", "kolkata", "delhi", "bangalore", "hyderabad", "kochi",
      "gujarat", "kerala", "maharashtra", "rajasthan", "karnataka",
      "singapore", "dubai", "uae", "pakistan", "myanmar", "bangladesh",
      "yemen", "egypt"],
     "REGIONAL",      0.50),
    ([], "LOCAL", 0.25),  # default fallback
]

# ── Transport mode score ──────────────────────────────────────────────────────
TRANSPORT_MODE_SCORES: dict[str, float] = {
    "sea":        1.0,   # largest volume; highest operational impact
    "multimodal": 0.9,   # combines multiple modes; compound risk
    "air":        0.6,   # high value, lower volume
    "rail":       0.5,
    "road":       0.4,
    "unknown":    0.3,
}

# ── Port relevance rules ──────────────────────────────────────────────────────
PORT_DIRECT_KEYWORDS:    list[str] = ["port", "jnpt", "nhava sheva", "terminal"]
PORT_ADJACENT_KEYWORDS:  list[str] = ["mumbai", "chennai", "kolkata", "kochi",
                                       "singapore", "dubai", "shanghai", "suez",
                                       "red sea"]

# ── Duration normalization ────────────────────────────────────────────────────
# Using log scale: score = log(1 + duration_h) / log(1 + MAX_DURATION_H)
DURATION_NORM_MAX_HOURS: float = 2160.0   # 90 days — upper bound for scoring


# ── DNA Similarity Weights ─────────────────────────────────────────────────────
# These determine how much each DNA dimension contributes to the similarity score.
# Documented as SupplyShield configurable assumptions — not industry standards.
@dataclass(frozen=True)
class DNASimilarityWeights:
    """
    Weights for the Disruption DNA similarity algorithm.

    All weights must sum to 1.0.

    Rationale:
      type        0.25 — disruption category is the strongest predictor of
                         which historical playbooks apply
      severity    0.20 — severity determines response urgency and resource scale
      region      0.20 — same region → same infrastructure constraints
      duration    0.15 — similar duration → similar recovery time horizon
      geo_scope   0.10 — regional vs international changes response strategy
      transport   0.05 — transport mode affects which routes are impacted
      capacity    0.05 — capacity reduction level affects fleet decisions
    """
    type:      float = 0.25
    severity:  float = 0.20
    region:    float = 0.20
    duration:  float = 0.15
    geo_scope: float = 0.10
    transport: float = 0.05
    capacity:  float = 0.05

    def __post_init__(self) -> None:
        total = (self.type + self.severity + self.region +
                 self.duration + self.geo_scope + self.transport + self.capacity)
        if abs(total - 1.0) > 1e-9:
            raise ValueError(f"DNA similarity weights must sum to 1.0, got {total}")

    def as_dict(self) -> dict[str, float]:
        return {
            "type": self.type,
            "severity": self.severity,
            "region": self.region,
            "duration": self.duration,
            "geo_scope": self.geo_scope,
            "transport": self.transport,
            "capacity": self.capacity,
        }


@dataclass(frozen=True)
class DNAConfig:
    """Top-level DNA configuration — injected into DNA service."""
    weights: DNASimilarityWeights = field(default_factory=DNASimilarityWeights)
    # Minimum similarity score (0–100) to include in results
    min_similarity_threshold: float = 20.0
    # Maximum historical results to return
    max_similar_results: int = 5


# ── Helpers ────────────────────────────────────────────────────────────────────

def normalize_duration(duration_hours: float) -> float:
    """Log-normalized duration score in [0, 1]."""
    if duration_hours <= 0:
        return 0.0
    return math.log(1.0 + duration_hours) / math.log(1.0 + DURATION_NORM_MAX_HOURS)


def classify_geo_scope(affected_region: str) -> tuple[str, float]:
    """Classify geographic scope from region string. Returns (label, score)."""
    region_lower = affected_region.lower()
    for keywords, label, score in GEO_SCOPE_RULES[:-1]:  # skip default last entry
        if any(kw in region_lower for kw in keywords):
            return label, score
    return GEO_SCOPE_RULES[-1][1], GEO_SCOPE_RULES[-1][2]  # LOCAL


def classify_port_relevance(disruption_type: str, affected_region: str) -> float:
    """Return port relevance score 0.0 / 0.5 / 1.0."""
    region_lower = affected_region.lower()
    if disruption_type == "port" or any(kw in region_lower for kw in PORT_DIRECT_KEYWORDS):
        return 1.0
    if any(kw in region_lower for kw in PORT_ADJACENT_KEYWORDS):
        return 0.5
    return 0.0


def classify_transport_mode(disruption_type: str, affected_region: str) -> tuple[str, float]:
    """Infer primary transport mode affected from type + region."""
    region_lower = affected_region.lower()
    type_lower = disruption_type.lower()

    # Explicit port → sea
    if type_lower == "port":
        return "sea", TRANSPORT_MODE_SCORES["sea"]

    # Explicit clues in region
    sea_clues = ["sea", "ocean", "port", "canal", "strait", "gulf", "bay"]
    if any(c in region_lower for c in sea_clues):
        return "sea", TRANSPORT_MODE_SCORES["sea"]

    air_clues = ["airport", "air cargo", "aviation"]
    if any(c in region_lower for c in air_clues):
        return "air", TRANSPORT_MODE_SCORES["air"]

    rail_clues = ["railway", "rail", "train"]
    if any(c in region_lower for c in rail_clues):
        return "rail", TRANSPORT_MODE_SCORES["rail"]

    road_clues = ["road", "highway", "expressway", "border crossing", "border"]
    if any(c in region_lower for c in road_clues):
        return "road", TRANSPORT_MODE_SCORES["road"]

    # Transport disruption type defaults to multimodal
    if type_lower == "transport":
        return "multimodal", TRANSPORT_MODE_SCORES["multimodal"]

    # Weather disruptions near coast → sea
    if type_lower == "weather":
        coast_clues = ["coast", "cyclone", "typhoon", "flood", "sea"]
        if any(c in region_lower for c in coast_clues):
            return "sea", TRANSPORT_MODE_SCORES["sea"]
        return "road", TRANSPORT_MODE_SCORES["road"]

    return "unknown", TRANSPORT_MODE_SCORES["unknown"]


def compute_capacity_impact(severity: int, disruption_type: str) -> float:
    """Estimate capacity impact score from severity + type (0.0–1.0)."""
    base = severity / 10.0  # 1–10 → 0.1–1.0

    # Type multipliers
    type_boost: dict[str, float] = {
        "port":        1.0,
        "transport":   0.9,
        "weather":     0.85,
        "geopolitical":0.8,
        "supplier":    0.7,
        "regulatory":  0.5,
        "cyber":       0.4,
        "demand":      0.3,
    }
    multiplier = type_boost.get(disruption_type.lower(), 0.6)
    return min(1.0, base * multiplier)


def compute_region_score(affected_region: str) -> float:
    """
    Produce a region affinity score in [0, 1].

    Uses a stable hash of the normalised region string, bucketed into 0.05 steps.
    Two disruptions in the same region get the same score → maximum region similarity.
    Disruptions in different regions get different scores → reduced similarity.

    This is deliberately simple and transparent — not a geo-distance calculation.
    """
    normalised = affected_region.strip().lower()
    # Use Python's hash for determinism within a single run; stabilize with seed
    # We want the same region to always map to the same bucket.
    # Use sum of character ordinals * position, mod 20 to get 20 buckets.
    h = sum((i + 1) * ord(c) for i, c in enumerate(normalised)) % 20
    return round(h / 20.0, 2)


DEFAULT_DNA_CONFIG = DNAConfig()
