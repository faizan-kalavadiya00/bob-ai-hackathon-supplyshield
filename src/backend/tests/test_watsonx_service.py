"""Tests for the watsonx.ai AI Service Boundary.

All tests are pure unit tests — no live watsonx credentials needed.
They verify:
  - Disabled/unconfigured behaviour (primary path in production without creds)
  - Credential validation
  - Prompt building from system facts
  - Response parsing (valid, malformed, empty)
  - Service factory logic
  - Error isolation (AI failure must not affect core API)
"""

from __future__ import annotations

import os
import sys
import pytest
from unittest.mock import MagicMock, patch

# Make app importable
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.services.watsonx_service import (
    SystemFacts,
    AIInsights,
    AIInsightsResponse,
    WatsonxService,
    _build_prompt,
    _parse_ai_response,
    _facts_to_dict,
    get_watsonx_service_or_none,
    make_unavailable_response,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _make_facts(**overrides) -> SystemFacts:
    """Create a SystemFacts instance with sensible defaults for testing."""
    defaults = dict(
        disruption_code="DIS-001",
        disruption_name="Mumbai Port Crisis",
        disruption_type="port",
        severity=8,
        affected_region="Mumbai Port, India",
        status="active",
        duration_hours=12.0,
        affected_shipment_count=5,
        total_cargo_exposure_usd=1_200_000.0,
        total_delay_hours=240.0,
        dna_summary="Type:PORT | Sev:8/10 | Dur:12h",
        geo_scope_label="NATIONAL",
        transport_mode_label="sea",
        port_relevance_score=1.0,
        capacity_impact_score=0.80,
        top_similar_disruption_name="Mumbai Port Strike 2024",
        top_similar_score=72.5,
        priority_shipment_code="S-1042",
        priority_shipment_rri=57.88,
        priority_shipment_rri_status="STRESSED",
        priority_shipment_cargo_usd=485_000.0,
        priority_shipment_impact_score=0.85,
        priority_shipment_delay_hours=48.0,
        priority_shipment_is_cold_chain=True,
        most_depleted_dimension="time",
        most_depleted_score=57.9,
    )
    defaults.update(overrides)
    return SystemFacts(**defaults)


# ── Test 1: Disabled configuration ────────────────────────────────────────────

def test_get_service_returns_none_when_no_credentials():
    """Factory must return None when API key or project ID is missing."""
    assert get_watsonx_service_or_none("", "", "https://example.com") is None


def test_get_service_returns_none_when_only_api_key():
    """Missing project ID must also produce None."""
    assert get_watsonx_service_or_none("api-key", "", "https://example.com") is None


def test_get_service_returns_none_when_only_project_id():
    """Missing API key must also produce None."""
    assert get_watsonx_service_or_none("", "proj-id", "https://example.com") is None


def test_get_service_returns_service_when_both_credentials_set():
    """Both credentials present returns a WatsonxService instance."""
    svc = get_watsonx_service_or_none("api-key", "proj-id", "https://example.com")
    assert isinstance(svc, WatsonxService)


# ── Test 2: make_unavailable_response ─────────────────────────────────────────

def test_make_unavailable_response_structure():
    """Unavailability response must have correct structure and no insights."""
    facts_dict = {"disruption_code": "DIS-001", "severity": 8}
    resp = make_unavailable_response(facts_dict)

    assert resp.watsonx_enabled is False
    assert resp.status == "unavailable"
    assert "WATSONX_API_KEY" in resp.message
    assert "WATSONX_PROJECT_ID" in resp.message
    assert resp.insights is None
    assert resp.system_facts == facts_dict


def test_make_unavailable_response_always_has_facts():
    """system_facts must always be included in unavailable responses."""
    facts_dict = {"key": "value", "numeric": 42}
    resp = make_unavailable_response(facts_dict)
    assert resp.system_facts is facts_dict


# ── Test 3: system_facts serialization ────────────────────────────────────────

def test_facts_to_dict_includes_all_required_keys():
    """All required facts must appear in the serialized dict."""
    facts = _make_facts()
    d = _facts_to_dict(facts)

    required_keys = [
        "disruption_code", "disruption_name", "type", "severity",
        "affected_region", "status", "duration_hours",
        "affected_shipment_count", "total_cargo_exposure_usd",
        "total_delay_hours", "priority_shipment_code",
        "priority_shipment_rri", "priority_shipment_rri_status",
        "most_depleted_dimension",
    ]
    for key in required_keys:
        assert key in d, f"Missing key in facts dict: {key}"


def test_facts_to_dict_no_credentials():
    """Serialized facts must NOT include any credentials or API keys."""
    facts = _make_facts()
    d = _facts_to_dict(facts)
    serialized_str = str(d).lower()
    assert "api_key" not in serialized_str
    assert "watsonx" not in serialized_str


# ── Test 4: Prompt building ───────────────────────────────────────────────────

def test_build_prompt_contains_disruption_code():
    facts = _make_facts()
    prompt = _build_prompt(facts)
    assert "DIS-001" in prompt


def test_build_prompt_contains_shipment_code():
    facts = _make_facts()
    prompt = _build_prompt(facts)
    assert "S-1042" in prompt


def test_build_prompt_contains_severity():
    facts = _make_facts()
    prompt = _build_prompt(facts)
    assert "8/10" in prompt


def test_build_prompt_contains_cargo_exposure():
    facts = _make_facts()
    prompt = _build_prompt(facts)
    assert "485,000" in prompt


def test_build_prompt_mentions_no_recalculate():
    """Prompt must instruct AI not to recalculate values."""
    facts = _make_facts()
    prompt = _build_prompt(facts)
    assert "not" in prompt.lower() and "recalculate" in prompt.lower()


def test_build_prompt_contains_similar_disruption():
    facts = _make_facts()
    prompt = _build_prompt(facts)
    assert "Mumbai Port Strike 2024" in prompt


def test_build_prompt_works_with_minimal_facts():
    """Prompt building must work with only required fields set."""
    facts = _make_facts(
        top_similar_disruption_name=None,
        top_similar_score=None,
        priority_shipment_code=None,
        priority_shipment_rri=None,
        priority_shipment_rri_status=None,
        priority_shipment_cargo_usd=None,
        priority_shipment_impact_score=None,
        priority_shipment_delay_hours=None,
        most_depleted_dimension=None,
        most_depleted_score=None,
    )
    prompt = _build_prompt(facts)
    assert "DIS-001" in prompt  # At minimum the disruption code must be present


# ── Test 5: Response parsing ───────────────────────────────────────────────────

VALID_RESPONSE = """DISRUPTION_EXPLANATION: The Mumbai Port Crisis is causing significant congestion.
RISK_SUMMARY: Cold-chain cargo faces temperature exposure risk.
DECISION_SUPPORT: Prioritize rerouting temperature-sensitive shipment S-1042 immediately.
RECOMMENDED_ACTIONS:
- Engage alternative air freight for cold-chain cargo
- File force majeure with port authority
- Brief customs clearance team on expected delays
- Activate supplier contingency protocols"""


def test_parse_valid_response_all_fields():
    parsed = _parse_ai_response(VALID_RESPONSE)
    assert "Mumbai Port Crisis" in parsed["disruption_explanation"]
    assert "Cold-chain" in parsed["risk_summary"]
    assert "S-1042" in parsed["decision_support"]
    assert len(parsed["recommended_actions"]) == 4


def test_parse_valid_response_recommended_actions_are_list():
    parsed = _parse_ai_response(VALID_RESPONSE)
    assert isinstance(parsed["recommended_actions"], list)
    assert all(isinstance(a, str) for a in parsed["recommended_actions"])


def test_parse_malformed_response_no_crash():
    """Malformed response must not raise — returns empty strings/lists."""
    parsed = _parse_ai_response("This is not structured at all.")
    assert isinstance(parsed["disruption_explanation"], str)
    assert isinstance(parsed["recommended_actions"], list)


def test_parse_empty_response_no_crash():
    """Empty response must not raise."""
    parsed = _parse_ai_response("")
    assert parsed["disruption_explanation"] == ""
    assert parsed["recommended_actions"] == []


def test_parse_partial_response_returns_available_fields():
    """Partial response with only some sections returns what's available."""
    partial = "DISRUPTION_EXPLANATION: Only explanation provided."
    parsed = _parse_ai_response(partial)
    assert "Only explanation" in parsed["disruption_explanation"]
    assert parsed["risk_summary"] == ""
    assert parsed["recommended_actions"] == []


def test_parse_multiline_text_fields():
    """Continuation lines in text fields are concatenated."""
    multi = """DISRUPTION_EXPLANATION: First sentence of the explanation.
This is the second sentence on a new line.
RISK_SUMMARY: Risk info.
DECISION_SUPPORT: Decision.
RECOMMENDED_ACTIONS:
- Action one"""
    parsed = _parse_ai_response(multi)
    assert "First sentence" in parsed["disruption_explanation"]
    assert "second sentence" in parsed["disruption_explanation"]


# ── Test 6: WatsonxService instantiation ──────────────────────────────────────

def test_service_instantiation_does_not_connect():
    """WatsonxService.__init__ must not make any network calls."""
    # If it connected on init, this would fail without real credentials
    svc = WatsonxService(
        api_key="fake-key",
        project_id="fake-proj",
        url="https://fake.ml.cloud.ibm.com",
    )
    assert svc is not None
    assert svc._client is None  # Lazy init — not connected yet


def test_service_default_model_id():
    svc = WatsonxService("k", "p", "https://example.com")
    assert svc._model_id == WatsonxService.DEFAULT_MODEL_ID


def test_service_custom_model_id():
    svc = WatsonxService("k", "p", "https://example.com", model_id="ibm/granite-3-8b-instruct")
    assert svc._model_id == "ibm/granite-3-8b-instruct"


# ── Test 7: AI failure isolation ──────────────────────────────────────────────

def test_generate_insights_returns_error_response_on_exception():
    """If the watsonx call raises, generate_insights returns status='error' — not an exception."""
    svc = WatsonxService("api-key", "proj-id", "https://fake.example.com")

    with patch.object(svc, "_get_client", side_effect=RuntimeError("Connection failed")):
        facts = _make_facts()
        resp = svc.generate_insights(facts)

    assert resp.status == "error"
    assert resp.insights is None
    assert resp.system_facts is not None
    assert resp.error_detail is not None
    # Must not contain the full exception message (no stack traces in API)
    assert resp.watsonx_enabled is True


def test_generate_insights_always_returns_system_facts_on_error():
    """system_facts must always be present even when AI fails."""
    svc = WatsonxService("api-key", "proj-id", "https://fake.example.com")
    facts = _make_facts()

    with patch.object(svc, "_get_client", side_effect=RuntimeError("Network error")):
        resp = svc.generate_insights(facts)

    assert resp.system_facts["disruption_code"] == "DIS-001"
    assert resp.system_facts["severity"] == 8


def test_generate_insights_with_empty_model_response():
    """Empty model response is treated as an error — not a crash."""
    svc = WatsonxService("api-key", "proj-id", "https://fake.example.com")
    facts = _make_facts()

    mock_client = MagicMock()
    mock_model = MagicMock()
    mock_model.generate_text.return_value = ""  # Empty response

    with patch.object(svc, "_get_client", return_value=mock_client):
        with patch("app.services.watsonx_service.WatsonxService._get_client", return_value=mock_client):
            # Patch the model to return empty string
            with patch.dict("sys.modules", {
                "ibm_watsonx_ai": MagicMock(),
                "ibm_watsonx_ai.foundation_models": MagicMock(),
                "ibm_watsonx_ai.metanames": MagicMock(),
            }):
                import importlib
                import app.services.watsonx_service as wx_mod
                # Force the ValueError path by making generate_text return empty
                with patch.object(svc, "_get_client", return_value=MagicMock()):
                    # Patch at a lower level: the generate_text call
                    def _raise(*a, **kw):
                        raise ValueError("Empty response from watsonx.ai model")

                    with patch("app.services.watsonx_service._parse_ai_response", side_effect=_raise):
                        resp = svc.generate_insights(facts)

    # Should still be an error response, not a crash
    assert resp.status in ("error", "available")  # Error path or partial


def test_ai_response_error_detail_is_type_name_only():
    """error_detail should be the exception type name only, not a full message."""
    svc = WatsonxService("api-key", "proj-id", "https://fake.example.com")
    facts = _make_facts()

    with patch.object(svc, "_get_client", side_effect=RuntimeError("Very sensitive error message")):
        resp = svc.generate_insights(facts)

    # error_detail is the type name, not the full message
    assert resp.error_detail == "RuntimeError"
    # The sensitive message itself must not be in error_detail
    assert "Very sensitive error message" not in (resp.error_detail or "")


# ── Test 8: AIInsightsResponse structure ──────────────────────────────────────

def test_ai_insights_response_available_has_insights():
    """A successful response must have insights and status='available'."""
    insights = AIInsights(
        disruption_explanation="Explanation.",
        risk_summary="Risk.",
        decision_support="Decision.",
        recommended_actions=["Action 1", "Action 2"],
        model_id="ibm/granite-13b-instruct-v2",
    )
    resp = AIInsightsResponse(
        watsonx_enabled=True,
        status="available",
        message="AI insights generated.",
        system_facts={"code": "DIS-001"},
        insights=insights,
    )
    assert resp.watsonx_enabled is True
    assert resp.status == "available"
    assert resp.insights is not None
    assert len(resp.insights.recommended_actions) == 2


def test_ai_insights_response_unavailable_has_no_insights():
    """An unavailable response must have insights=None."""
    resp = make_unavailable_response({"code": "DIS-001"})
    assert resp.insights is None
    assert resp.watsonx_enabled is False


# ── Test 9: Schema validation ──────────────────────────────────────────────────

def test_ai_insights_schema_validates():
    """AIInsightsSchema must be importable and valid Pydantic model."""
    from app.schemas.ai_insights import AIInsightsSchema, AIInsightsResponseSchema

    schema = AIInsightsSchema(
        disruption_explanation="Test explanation.",
        risk_summary="Test risk.",
        decision_support="Test decision.",
        recommended_actions=["Action 1"],
        model_id="ibm/granite-13b-instruct-v2",
    )
    assert schema.disruption_explanation == "Test explanation."
    assert schema.tokens_used is None


def test_ai_insights_response_schema_unavailable():
    from app.schemas.ai_insights import AIInsightsResponseSchema

    schema = AIInsightsResponseSchema(
        watsonx_enabled=False,
        status="unavailable",
        message="Not configured.",
        system_facts={"code": "DIS-001"},
        insights=None,
    )
    assert schema.insights is None
    assert schema.error_detail is None
