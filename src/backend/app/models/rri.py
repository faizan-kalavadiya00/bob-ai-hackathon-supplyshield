"""RRISnapshot ORM model."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class RRISnapshot(Base):
    """Point-in-time Resilience Remaining Index snapshot.

    RRI values are ALWAYS computed by the deterministic backend engine.
    This table stores the results for trending and audit purposes.
    """

    __tablename__ = "rri_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    # 0.0 = bankrupt, 1.0 = fully resilient
    rri_value: Mapped[float] = mapped_column(Float, nullable=False)
    # JSON breakdown of component scores
    component_scores: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    def __repr__(self) -> str:
        return f"<RRISnapshot {self.entity_type}:{self.entity_id} rri={self.rri_value:.3f}>"
