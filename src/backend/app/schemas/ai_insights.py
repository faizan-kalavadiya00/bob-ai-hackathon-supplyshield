"""Pydantic schemas for the AI Decision Support API boundary.

These schemas define the contract between the watsonx.ai service layer
and the REST API. They are separate from disruption/resilience schemas
to keep the AI boundary explicit and independently evolvable.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class AIInsightsSchema(BaseModel):
    """AI-generated textual insights. All fields are LLM output."""

    disruption_explanation: str
    risk_summary: str
    decision_support: str
    recommended_actions: list[str]
    model_id: str
    tokens_used: int | None = None


class AIInsightsResponseSchema(BaseModel):
    """Full AI Decision Support API response.

    system_facts is always present and contains pre-calculated deterministic
    values from the SupplyShield engine. insights is null when watsonx is
    disabled or when insight generation fails.

    Clients must NOT use insights values as operational metrics — they are
    explanatory text only. All numerical operational values come from the
    deterministic system_facts dict.
    """

    watsonx_enabled: bool
    status: str  # "available" | "unavailable" | "error"
    message: str
    system_facts: dict[str, Any]
    insights: AIInsightsSchema | None = None
    error_detail: str | None = None
