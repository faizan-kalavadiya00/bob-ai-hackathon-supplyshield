"""SimulationRun ORM model."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SimulationRun(Base):
    __tablename__ = "simulation_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    scenario_type: Mapped[str] = mapped_column(String(100), nullable=False)
    # Input parameters used for this simulation
    parameters: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    # Computed output
    result_summary: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    rri_impact: Mapped[float | None] = mapped_column(Float)
    created_by: Mapped[str] = mapped_column(String(200), nullable=False, default="system")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<SimulationRun {self.id} {self.scenario_type}>"
