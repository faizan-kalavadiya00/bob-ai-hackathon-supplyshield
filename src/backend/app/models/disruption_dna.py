"""DisruptionDNA ORM model.

Stores the structured DNA fingerprint of a disruption event.
DNA is generated deterministically from disruption attributes.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class DisruptionDNA(Base):
    __tablename__ = "disruption_dna"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    disruption_id: Mapped[int] = mapped_column(
        ForeignKey("disruptions.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    # ── Core DNA attributes ────────────────────────────────────────────────────
    # Normalized 0.0–1.0 values used for similarity comparison

    # Type encoding (0.0–1.0 via ordered mapping)
    type_score: Mapped[float] = mapped_column(Float, nullable=False)
    # Raw type string for display
    type_label: Mapped[str] = mapped_column(String(50), nullable=False)

    # Severity 1–10 → normalized 0.0–1.0
    severity_score: Mapped[float] = mapped_column(Float, nullable=False)
    severity_raw: Mapped[int] = mapped_column(Integer, nullable=False)

    # Duration in hours → normalized via log scale (0.0–1.0)
    duration_score: Mapped[float] = mapped_column(Float, nullable=False)
    duration_hours: Mapped[float] = mapped_column(Float, nullable=False)

    # Geographic scope: LOCAL/REGIONAL/NATIONAL/INTERNATIONAL → 0.25/0.50/0.75/1.0
    geo_scope_score: Mapped[float] = mapped_column(Float, nullable=False)
    geo_scope_label: Mapped[str] = mapped_column(String(30), nullable=False)

    # Transport mode affected: sea/air/road/rail/multimodal/unknown → 0–5 ordinal → /5
    transport_mode_score: Mapped[float] = mapped_column(Float, nullable=False)
    transport_mode_label: Mapped[str] = mapped_column(String(30), nullable=False)

    # Capacity impact: derived from severity + type (0.0–1.0)
    capacity_impact_score: Mapped[float] = mapped_column(Float, nullable=False)

    # Port/route relevance: 0.0 (not port), 0.5 (port-adjacent), 1.0 (port-direct)
    port_relevance_score: Mapped[float] = mapped_column(Float, nullable=False)

    # Region hash bucket (0.0–1.0) — same region → close score
    region_score: Mapped[float] = mapped_column(Float, nullable=False)
    region_label: Mapped[str] = mapped_column(String(200), nullable=False)

    # Shipment impact profile (from shipment_disruptions)
    avg_impact_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    affected_shipment_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Human-readable summary of the DNA
    dna_summary: Mapped[str | None] = mapped_column(Text)

    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationship back to disruption
    disruption: Mapped["Disruption"] = relationship(  # noqa: F821
        "Disruption", back_populates="dna", foreign_keys=[disruption_id]
    )

    def __repr__(self) -> str:
        return f"<DisruptionDNA disruption_id={self.disruption_id} type={self.type_label}>"
