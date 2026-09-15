"""Route ORM model."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Route(Base):
    __tablename__ = "routes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    route_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    route_name: Mapped[str] = mapped_column(String(200), nullable=False)
    origin: Mapped[str] = mapped_column(String(200), nullable=False)
    destination: Mapped[str] = mapped_column(String(200), nullable=False)
    distance_km: Mapped[float] = mapped_column(Float, nullable=False)
    duration_hours: Mapped[float] = mapped_column(Float, nullable=False)
    # 0.0–1.0; higher = riskier
    risk_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.2)
    capacity_kg: Mapped[float] = mapped_column(Float, nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    transport_mode: Mapped[str] = mapped_column(String(50), nullable=False, default="multimodal")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    shipments: Mapped[list["Shipment"]] = relationship(  # noqa: F821
        "Shipment", back_populates="route", lazy="select"
    )

    def __repr__(self) -> str:
        return f"<Route {self.route_code} {self.origin}→{self.destination}>"
