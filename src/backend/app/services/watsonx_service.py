"""SupplyShield watsonx.ai AI Service Boundary.

This module provides the OPTIONAL AI explanation layer for SupplyShield.
It consumes only pre-calculated deterministic facts from the DNA, similarity,
impact, and resilience services — it does NOT produce or overwrite any
numerical values (RRI, DNA scores, wallet balances, similarity scores, etc.).

When watsonx is not configured (WATSONX_API_KEY and WATSONX_PROJECT_ID
environment variables not set), this service returns a structured response
indicating unavailability. All core SupplyShield APIs continue working normally.

Design principles:
  1. AI consumes facts; deterministic services produce facts.
  2. AI failure must never break core disruption or resilience APIs.
  3. Generated text is clearly labelled as AI output, not operational data.
  4. No credential is ever logged or included in API responses.
  5. The prompt contains only values from the deterministic engine.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class SystemFacts:
    """Pre-calculated deterministic facts passed READ-ONLY to the AI layer.

    These values are produced by deterministic Python services.
    The AI may interpret but not modify or recalculate them.
    """
    disruption_code: str
    disruption_name: str
    disruption_type: str
    severity: int
    affected_region: str
    status: str
    duration_hours: float
    affected_shipment_count: int
    total_cargo_exposure_usd: float
    total_delay_hours: float
    # DNA facts (all deterministic)
    dna_summary: str | None = None
    geo_scope_label: str | None = None
    transport_mode_label: str | None = None
    port_relevance_score: float | None = None
    capacity_impact_score: float | None = None
    # Similarity facts
    top_similar_disruption_name: str | None = None
    top_similar_score: float | None = None
    # Priority shipment facts
    priority_shipment_code: str | None = None
    priority_shipment_rri: float | None = None
    priority_shipment_rri_status: str | None = None
    priority_shipment_cargo_usd: float | None = None
    priority_shipment_impact_score: float | None = None
    priority_shipment_delay_hours: float | None = None
    priority_shipment_is_cold_chain: bool = False
    # Wallet facts (most depleted dimension)
    most_depleted_dimension: str | None = None
    most_depleted_score: float | None = None


@dataclass
class AIInsights:
    """Structured AI-generated insights. All text is clearly AI-generated."""
    disruption_explanation: str
    risk_summary: str
    decision_support: str
    recommended_actions: list[str]
    model_id: str
    tokens_used: int | None = None


@dataclass
class AIInsightsResponse:
    """Full response from the AI service boundary."""
    watsonx_enabled: bool
    status: str  # "available" | "unavailable" | "error"
    message: str
    system_facts: dict[str, Any]  # Always present — the deterministic facts used
    insights: AIInsights | None = None
    error_detail: str | None = None


def _facts_to_dict(facts: SystemFacts) -> dict[str, Any]:
    """Convert SystemFacts to a serializable dict for API responses."""
    return {
        "disruption_code": facts.disruption_code,
        "disruption_name": facts.disruption_name,
        "type": facts.disruption_type,
        "severity": facts.severity,
        "affected_region": facts.affected_region,
        "status": facts.status,
        "duration_hours": facts.duration_hours,
        "affected_shipment_count": facts.affected_shipment_count,
        "total_cargo_exposure_usd": facts.total_cargo_exposure_usd,
        "total_delay_hours": facts.total_delay_hours,
        "geo_scope": facts.geo_scope_label,
        "transport_mode": facts.transport_mode_label,
        "port_relevance_score": facts.port_relevance_score,
        "capacity_impact_score": facts.capacity_impact_score,
        "top_similar_disruption": facts.top_similar_disruption_name,
        "top_similar_score": facts.top_similar_score,
        "priority_shipment_code": facts.priority_shipment_code,
        "priority_shipment_rri": facts.priority_shipment_rri,
        "priority_shipment_rri_status": facts.priority_shipment_rri_status,
        "priority_shipment_cargo_usd": facts.priority_shipment_cargo_usd,
        "priority_shipment_impact_score": facts.priority_shipment_impact_score,
        "priority_shipment_delay_hours": facts.priority_shipment_delay_hours,
        "priority_shipment_is_cold_chain": facts.priority_shipment_is_cold_chain,
        "most_depleted_dimension": facts.most_depleted_dimension,
        "most_depleted_score": facts.most_depleted_score,
    }


def _build_prompt(facts: SystemFacts) -> str:
    """Build a structured prompt from deterministic facts only.

    The prompt is constructed entirely from pre-calculated system facts.
    No values are invented or estimated in the prompt construction.
    """
    priority_section = ""
    if facts.priority_shipment_code:
        cold = " (COLD-CHAIN)" if facts.priority_shipment_is_cold_chain else ""
        rri_val = f"{facts.priority_shipment_rri:.1f}" if facts.priority_shipment_rri is not None else "N/A"
        rri_status = facts.priority_shipment_rri_status or "N/A"
        cargo = f"${facts.priority_shipment_cargo_usd:,.0f}" if facts.priority_shipment_cargo_usd is not None else "N/A"
        impact = f"{facts.priority_shipment_impact_score:.0%}" if facts.priority_shipment_impact_score is not None else "N/A"
        delay = f"{facts.priority_shipment_delay_hours:.0f}h" if facts.priority_shipment_delay_hours is not None else "N/A"
        depleted = "N/A"
        if facts.most_depleted_dimension and facts.most_depleted_score is not None:
            depleted = f"{facts.most_depleted_dimension.upper()} ({facts.most_depleted_score:.0f}% remaining)"
        priority_section = (
            f"\nHighest-priority affected shipment: {facts.priority_shipment_code}{cold}"
            f"\n  Resilience Remaining Index (RRI): {rri_val} — Status: {rri_status}"
            f"\n  Cargo value: {cargo}"
            f"\n  Disruption impact score: {impact}"
            f"\n  Delay introduced: {delay}"
            f"\n  Most depleted wallet dimension: {depleted}"
        )

    similarity_section = ""
    if facts.top_similar_disruption_name:
        score_str = f"{facts.top_similar_score:.0f}%" if facts.top_similar_score is not None else "N/A"
        similarity_section = (
            f"\nMost similar historical disruption: {facts.top_similar_disruption_name}"
            f" (similarity score: {score_str})"
        )

    port_rel = f"{(facts.port_relevance_score or 0) * 100:.0f}%"
    cap_impact = f"{(facts.capacity_impact_score or 0) * 100:.0f}%"

    prompt = f"""You are an operational supply-chain resilience analyst. You are analyzing a live disruption event and must provide decision support to an operations team.

IMPORTANT RULES:
- You are given pre-calculated system facts from a deterministic analytics engine.
- Do NOT recalculate, estimate, or modify any numerical values provided.
- Your role is ONLY to interpret the facts and provide operational guidance.
- Be concise and specific. Do not repeat numbers verbatim — interpret them operationally.

=== DISRUPTION FACTS (SupplyShield deterministic engine) ===
Code: {facts.disruption_code}
Name: {facts.disruption_name}
Type: {facts.disruption_type.upper()}
Severity: {facts.severity}/10
Status: {facts.status.upper()}
Region: {facts.affected_region}
Duration: {facts.duration_hours:.0f} hours elapsed
Affected shipments: {facts.affected_shipment_count}
Total cargo exposure: ${facts.total_cargo_exposure_usd:,.0f}
Total delay impact: {facts.total_delay_hours:.0f} hours
Geographic scope: {facts.geo_scope_label or 'N/A'}
Transport mode: {facts.transport_mode_label or 'N/A'}
Port relevance: {port_rel}
Capacity impact: {cap_impact}{similarity_section}{priority_section}

DNA summary: {facts.dna_summary or 'N/A'}

=== YOUR TASK ===
Based ONLY on the system facts above, provide exactly this structure:

DISRUPTION_EXPLANATION: <2-3 sentences explaining what is happening operationally and why it matters>
RISK_SUMMARY: <2-3 sentences on the most critical risk factors and their operational significance>
DECISION_SUPPORT: <2-3 sentences on what the operations team should focus on first and why>
RECOMMENDED_ACTIONS:
- <specific action 1>
- <specific action 2>
- <specific action 3>
- <specific action 4>

Respond with ONLY the structured text above. No preamble, no additional sections."""
    return prompt


def _parse_ai_response(raw_text: str) -> dict[str, Any]:
    """Parse the structured AI response into components.

    Returns a dict with all four keys. Missing sections get empty strings/lists
    rather than raising, ensuring resilience to partial model responses.
    """
    result: dict[str, Any] = {
        "disruption_explanation": "",
        "risk_summary": "",
        "decision_support": "",
        "recommended_actions": [],
    }

    current_key: str | None = None

    for line in raw_text.strip().splitlines():
        line = line.strip()
        if not line:
            continue

        if line.startswith("DISRUPTION_EXPLANATION:"):
            current_key = "disruption_explanation"
            result[current_key] = line[len("DISRUPTION_EXPLANATION:"):].strip()
        elif line.startswith("RISK_SUMMARY:"):
            current_key = "risk_summary"
            result[current_key] = line[len("RISK_SUMMARY:"):].strip()
        elif line.startswith("DECISION_SUPPORT:"):
            current_key = "decision_support"
            result[current_key] = line[len("DECISION_SUPPORT:"):].strip()
        elif line.startswith("RECOMMENDED_ACTIONS:"):
            current_key = "recommended_actions"
        elif line.startswith("- ") and current_key == "recommended_actions":
            result["recommended_actions"].append(line[2:].strip())
        elif current_key and current_key != "recommended_actions":
            # Continuation line for text fields
            existing = result[current_key]
            result[current_key] = (existing + " " + line).strip() if existing else line

    return result


class WatsonxService:
    """
    AI service boundary for SupplyShield.

    Consumes pre-calculated deterministic facts and generates human-readable
    operational insights using IBM watsonx.ai.

    When not configured, the get_watsonx_service_or_none() factory returns None
    and callers use make_unavailable_response() instead.

    Failures in this service must not propagate to core disruption or
    resilience API endpoints.
    """

    DEFAULT_MODEL_ID = "ibm/granite-13b-instruct-v2"

    def __init__(
        self,
        api_key: str,
        project_id: str,
        url: str,
        model_id: str = DEFAULT_MODEL_ID,
    ) -> None:
        # Credentials stored but never logged or returned in responses
        self._api_key = api_key
        self._project_id = project_id
        self._url = url
        self._model_id = model_id
        self._client: Any | None = None
        logger.info("WatsonxService initialised (model=%s, url=%s)", model_id, url)

    def _get_client(self) -> Any:
        """Lazy-initialise the IBM watsonx.ai API client."""
        if self._client is not None:
            return self._client
        try:
            from ibm_watsonx_ai import Credentials, APIClient  # type: ignore[import]
            credentials = Credentials(url=self._url, api_key=self._api_key)
            self._client = APIClient(credentials)
            return self._client
        except ImportError as exc:
            raise RuntimeError(
                "ibm-watsonx-ai package not installed. "
                "Run: pip install ibm-watsonx-ai"
            ) from exc

    def generate_insights(self, facts: SystemFacts) -> AIInsightsResponse:
        """Generate AI insights from pre-calculated system facts.

        Returns AIInsightsResponse with status='available' on success,
        status='error' if the model call fails. The system_facts dict
        is always included so the frontend can show deterministic data
        even when AI fails.

        Raises nothing — all exceptions are caught and returned as
        error responses so the calling endpoint remains stable.
        """
        facts_dict = _facts_to_dict(facts)

        try:
            prompt = _build_prompt(facts)
            client = self._get_client()

            from ibm_watsonx_ai.foundation_models import ModelInference  # type: ignore[import]
            from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams  # type: ignore[import]

            model = ModelInference(
                model_id=self._model_id,
                api_client=client,
                project_id=self._project_id,
                params={
                    GenParams.MAX_NEW_TOKENS: 600,
                    GenParams.TEMPERATURE: 0.3,
                    GenParams.REPETITION_PENALTY: 1.1,
                },
            )

            raw_response = model.generate_text(prompt=prompt)

            if not raw_response or not str(raw_response).strip():
                raise ValueError("Empty response from watsonx.ai model")

            parsed = _parse_ai_response(str(raw_response))

            # Ensure non-empty fallbacks so the panel always renders
            insights = AIInsights(
                disruption_explanation=(
                    parsed["disruption_explanation"]
                    or "Disruption explanation not available in model response."
                ),
                risk_summary=(
                    parsed["risk_summary"]
                    or "Risk summary not available in model response."
                ),
                decision_support=(
                    parsed["decision_support"]
                    or "Decision support not available in model response."
                ),
                recommended_actions=(
                    parsed["recommended_actions"]
                    or ["Review affected shipments.", "Monitor resilience wallet dimensions."]
                ),
                model_id=self._model_id,
            )

            return AIInsightsResponse(
                watsonx_enabled=True,
                status="available",
                message="AI insights generated by IBM watsonx.ai.",
                system_facts=facts_dict,
                insights=insights,
            )

        except Exception as exc:  # pylint: disable=broad-except
            logger.warning(
                "watsonx.ai insight generation failed for disruption %s: %s",
                facts.disruption_code,
                exc,
            )
            return AIInsightsResponse(
                watsonx_enabled=True,
                status="error",
                message=(
                    "AI insights generation failed. "
                    "Deterministic system facts below remain accurate."
                ),
                system_facts=facts_dict,
                error_detail=type(exc).__name__,  # type only — no stack trace in API response
            )


# ── Module-level helpers used by routers ──────────────────────────────────────

def make_unavailable_response(facts_dict: dict[str, Any]) -> AIInsightsResponse:
    """Return a structured unavailability response when watsonx is not configured.

    The system_facts dict is always populated so the frontend can display
    deterministic data alongside the unavailability notice.
    """
    return AIInsightsResponse(
        watsonx_enabled=False,
        status="unavailable",
        message=(
            "IBM watsonx.ai is not configured. "
            "Set WATSONX_API_KEY and WATSONX_PROJECT_ID environment variables "
            "to enable AI insights. "
            "All system facts shown below are calculated by the deterministic engine."
        ),
        system_facts=facts_dict,
        insights=None,
    )


def get_watsonx_service_or_none(
    api_key: str,
    project_id: str,
    url: str,
    model_id: str = WatsonxService.DEFAULT_MODEL_ID,
) -> WatsonxService | None:
    """Return a WatsonxService if both credentials are configured, else None.

    This is the single factory used by all routers.
    Returns None when watsonx is disabled — callers must handle the None case
    by returning make_unavailable_response().
    """
    if api_key and project_id:
        return WatsonxService(
            api_key=api_key,
            project_id=project_id,
            url=url,
            model_id=model_id,
        )
    return None
