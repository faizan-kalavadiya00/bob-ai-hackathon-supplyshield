# SupplyShield Disruption DNA — Technical Reference

*Phase 4B — Disruption Management + Disruption DNA*

---

## 1. What Is Disruption DNA?

In SupplyShield, **Disruption DNA** is a structured, normalized fingerprint of a
disruption event. It encodes the key operational characteristics of a disruption
in a form that makes two disruptions **comparable**.

DNA is not a ML embedding or a vector produced by a language model.
It is a deterministic calculation performed on the disruption's own database attributes.
The same disruption will always produce the same DNA — the algorithm is fully
transparent and reproducible.

---

## 2. DNA Attributes

Each disruption DNA record contains the following normalized attributes (0.0–1.0 unless otherwise noted):

| Attribute | Source | Description |
|---|---|---|
| `type_score` | `disruption.type` | Operational impact of the disruption category (port=1.0 most severe) |
| `type_label` | `disruption.type` | Human-readable type string |
| `severity_score` | `disruption.severity / 10` | Normalized 1–10 severity |
| `severity_raw` | `disruption.severity` | Raw integer 1–10 |
| `duration_score` | log-normalized `duration_hours` | Long disruptions score higher; bounded at 2160h (90 days) |
| `duration_hours` | `end_time - start_time` | Actual duration in hours (elapsed time for active disruptions) |
| `geo_scope_score` | keyword match on `affected_region` | LOCAL=0.25 / REGIONAL=0.50 / NATIONAL=0.75 / INTERNATIONAL=1.0 |
| `geo_scope_label` | derived | One of LOCAL / REGIONAL / NATIONAL / INTERNATIONAL |
| `transport_mode_score` | keyword match on type + region | sea=1.0, multimodal=0.9, air=0.6, rail=0.5, road=0.4 |
| `transport_mode_label` | derived | Inferred primary transport mode |
| `capacity_impact_score` | `severity × type_multiplier` | Estimated capacity reduction 0.0–1.0 |
| `port_relevance_score` | type + region keywords | 1.0=port-direct, 0.5=port-adjacent, 0.0=non-port |
| `region_score` | stable hash of `affected_region` | Bucket score; same region → same score |
| `region_label` | `disruption.affected_region` | Raw region string from database |
| `avg_impact_score` | average of `shipment_disruptions.impact_score` | Mean disruption impact across linked shipments |
| `affected_shipment_count` | count of `shipment_disruptions` rows | From database — not estimated |

Implementation: [`app/services/dna_config.py`](../src/backend/app/services/dna_config.py) and
[`app/services/dna_service.py`](../src/backend/app/services/dna_service.py).

---

## 3. Similarity Algorithm

### 3.1 Overview

The similarity algorithm compares two disruption DNA records using a
**weighted absolute-difference** formula. It is fully deterministic and
does not use any machine learning.

### 3.2 Formula

```
For each dimension d in {type, severity, region, duration, geo_scope, transport, capacity}:

    diff(d)         = | subject_dna[d] - candidate_dna[d] |   ∈ [0, 1]
    contribution(d) = (1 - diff(d)) × weight(d)               ∈ [0, weight(d)]

total_weighted_similarity = Σ contribution(d)                  ∈ [0, 1]
similarity_score           = total_weighted_similarity × 100   ∈ [0, 100]
```

- A score of **100** means the two disruptions are identical on all dimensions.
- A score of **0** means they are maximally different on all dimensions.
- The score can only be 100 if both disruptions have the same type, severity,
  region hash, duration, geographic scope, transport mode, and capacity impact.

### 3.3 Similarity Weights

These weights are **SupplyShield configurable model assumptions**.
They are not industry standards. They can be adjusted in
[`app/services/dna_config.py`](../src/backend/app/services/dna_config.py).

| Dimension     | Default weight | Rationale |
|--------------|---------------|-----------|
| `type`       | 0.25 | Disruption category is the strongest predictor of which historical playbooks apply |
| `severity`   | 0.20 | Severity determines response urgency and resource scale |
| `region`     | 0.20 | Same region → same infrastructure constraints apply |
| `duration`   | 0.15 | Similar duration → similar recovery time horizon |
| `geo_scope`  | 0.10 | Regional vs international changes the response strategy |
| `transport`  | 0.05 | Transport mode affects which routes are impacted |
| `capacity`   | 0.05 | Capacity reduction level affects fleet decisions |
| **Total**    | **1.00** | |

### 3.4 Similarity Score Meaning

| Score range | Interpretation |
|---|---|
| 75–100 | Very similar — high confidence that historical playbook applies |
| 50–74  | Moderately similar — historical context is useful with adaptation |
| 30–49  | Partially similar — some dimensions match; review carefully |
| < 30   | Low similarity — filtered out by default threshold |

### 3.5 Match Quality per Dimension

Each dimension also carries a `match_quality` label:

| Quality  | Condition (contribution / weight) |
|----------|----------------------------------|
| STRONG   | ≥ 85 % of max weight             |
| MODERATE | 60 – 84 %                        |
| WEAK     | 35 – 59 %                        |
| NONE     | < 35 %                           |

---

## 4. Historical Playbook Connection

When a similar historical disruption is found, SupplyShield presents:

- The similarity score and which dimensions matched
- The disruption's description from the database (if it contains retrospective outcome text)
- A clear notice: **"No historical recovery outcome recorded."** when no outcome text exists

**Only outcomes that exist in the seeded PostgreSQL database are displayed.**
No outcomes are generated, guessed, or hallucinated.

Outcome text is extracted by checking the disruption description for retrospective
language keywords (e.g. "historical reference", "resolved", "recovery").

---

## 5. Mumbai Port Crisis (DIS-001) — Demo Example

### DNA

| Attribute | Value |
|---|---|
| Type | PORT (score: 1.0) |
| Severity | 8/10 (score: 0.80) |
| Duration | 12h elapsed (active, no end_time) |
| Geo Scope | NATIONAL (India keyword) |
| Transport | SEA (port type → sea) |
| Port Relevance | 1.0 (port-direct) |
| Capacity Impact | 0.80 (sev=8, type=port) |

### Most Similar Historical Disruption

**DIS-006 — Mumbai Port Strike 2024** (HISTORICAL, severity=7, port type)

Both are:
- Same type: PORT
- Same region keyword: Mumbai Port, India
- Similar severity (8 vs 7)
- Same transport mode: SEA
- Same port relevance: 1.0

Expected similarity score: **≥ 50** (varies with elapsed duration on active disruption).

---

## 6. Cascading Impact

The cascade view shows the **actual database relationships**:

```
DIS-001 Mumbai Port Crisis
    ↓
Mumbai Port, India  (affected_region)
    ↓
RT-028: Ahmedabad → Dubai (multimodal)  (via shipments.route_id)
    ↓
S-1042 — Ahmedabad → Dubai (AT_RISK)
    ↓
Pharmaceutical — $485,000  (+48h delay, impact=0.85, cold-chain)
```

No relationships are fabricated. Every link shown exists in the `shipment_disruptions`
table, joined through `shipments` and `routes`.

---

## 7. API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET`  | `/api/disruptions` | List all disruptions with aggregates; filter by `?status=active` etc. |
| `GET`  | `/api/disruptions/{id}` | Full disruption detail including DNA |
| `GET`  | `/api/disruptions/{id}/dna` | Raw DNA fingerprint |
| `GET`  | `/api/disruptions/{id}/similar` | Similar historical disruptions with scores |
| `GET`  | `/api/disruptions/{id}/impact` | Cascading impact view |

---

## 8. Implementation Files

| File | Responsibility |
|---|---|
| `app/models/disruption_dna.py` | ORM model for `disruption_dna` table |
| `app/services/dna_config.py` | All DNA weights, type scores, geo rules, helpers |
| `app/services/dna_service.py` | `generate_dna()` — deterministic DNA generation |
| `app/services/similarity_service.py` | `find_similar_disruptions()` — weighted comparison |
| `app/routers/disruptions.py` | 5 FastAPI endpoints |
| `app/schemas/disruption.py` | Pydantic I/O contracts |
| `migrations/versions/*.py` | Alembic migration adding `disruption_dna` table |
| `src/frontend/src/api/disruptions.ts` | Typed API client |
| `src/frontend/src/components/DNAPanel.tsx` | DNA fingerprint bar chart |
| `src/frontend/src/components/SimilarityPanel.tsx` | Historical similarity results |
| `src/frontend/src/components/CascadeView.tsx` | Cascading impact tree |
| `src/frontend/src/components/DisruptionBadges.tsx` | Severity/status/type badges |
| `src/frontend/src/pages/Disruptions.tsx` | Full disruption command center page |
| `tests/test_disruptions.py` | 48 tests (unit + DB integration) |

---

## 9. Design Constraints

1. **Deterministic only.** Every DNA score and similarity figure is produced by
   arithmetic on database values. The output is reproducible given the same data.

2. **No LLM, no ML.** The words "machine learning" do not appear in any claim about
   this feature's outputs. The algorithm is documented above and can be audited line by line.

3. **No invented values.** Aggregate figures (cargo exposure, delay, affected count)
   are computed from `shipment_disruptions` joined to `shipments`.
   If no rows exist, the API returns 0.

4. **Weights are configurable assumptions.** The `DNASimilarityWeights` dataclass
   validates that weights sum to 1.0 and is the single source of truth.

5. **Idempotent DNA generation.** Calling `generate_dna()` twice on the same
   disruption updates the existing record rather than creating a duplicate.

---

## 10. Test Coverage

```
tests/test_disruptions.py  48 tests  100% pass

Unit tests (no DB needed):
  - Weight sum validation
  - Type score ordering
  - Geo scope classification
  - Port relevance rules
  - Duration normalization + monotonicity
  - Transport mode inference
  - Capacity impact bounds
  - Region score determinism
  - Similarity score 0–100 bounds (fuzz test: 100 random pairs)
  - Similarity determinism
  - Match quality bands
  - DNA + SimilarityResult schema field coverage

DB integration tests (require DATABASE_SYNC_URL):
  - DIS-001 Mumbai Port Crisis exists
  - DIS-006 Prior Mumbai Port Strike exists (HISTORICAL)
  - S-1042 linked to DIS-001 (impact=0.85, delay=48h)
  - DNA generation is deterministic
  - DIS-001 affected shipment count ≥ 1
  - DIS-001 cargo exposure ≥ $485,000 (S-1042 alone)
  - DIS-006 appears in DIS-001 similarity results (score ≥ 30)
  - All similarity scores for DIS-001 are in [0, 100]
  - Disruption listing returns ≥ 30 records
  - DIS-001 total delay ≥ 48h (S-1042 alone)
```
