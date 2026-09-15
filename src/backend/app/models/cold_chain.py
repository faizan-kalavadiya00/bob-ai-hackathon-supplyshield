"""ColdChainReading ORM model."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ColdChainReading(Base):
    __tablename__ = "cold_chain_readings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    shipment_id: Mapped[int] = mapped_column(
        ForeignKey("shipments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sensor_id: Mapped[str] = mapped_column(String(50), nullable=False)
    temperature_c: Mapped[float] = mapped_column(Float, nullable=False)
    humidity_pct: Mapped[float | None] = mapped_column(Float)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    # True if outside the shipment's configured min/max temperature range
    is_breach: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Relationships
    shipment: Mapped["Shipment"] = relationship(  # noqa: F821
        "Shipment", back_populates="cold_chain_readings"
    )

    def __repr__(self) -> str:
        return (
            f"<ColdChainReading ship={self.shipment_id} "
            f"sensor={self.sensor_id} temp={self.temperature_c}°C "
            f"{'BREACH' if self.is_breach else 'ok'}>"
        )
