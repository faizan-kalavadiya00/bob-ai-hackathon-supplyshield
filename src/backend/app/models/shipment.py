"""Shipment ORM model."""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ShipmentStatus(str, enum.Enum):
    PLANNED = "planned"
    IN_TRANSIT = "in_transit"
    DELAYED = "delayed"
    AT_RISK = "at_risk"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class CargoPriority(str, enum.Enum):
    ROUTINE = "routine"
    STANDARD = "standard"
    HIGH = "high"
    CRITICAL = "critical"


class Shipment(Base):
    __tablename__ = "shipments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    shipment_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"), nullable=False, index=True)

    # Routing
    origin: Mapped[str] = mapped_column(String(200), nullable=False)
    destination: Mapped[str] = mapped_column(String(200), nullable=False)
    route_id: Mapped[int | None] = mapped_column(ForeignKey("routes.id"))

    # Cargo details
    cargo_type: Mapped[str] = mapped_column(String(100), nullable=False)
    cargo_value_usd: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0.0)
    weight_kg: Mapped[float] = mapped_column(Float, nullable=False)
    priority: Mapped[CargoPriority] = mapped_column(
        Enum(CargoPriority, name="cargo_priority"), nullable=False, default=CargoPriority.STANDARD
    )

    # State
    status: Mapped[ShipmentStatus] = mapped_column(
        Enum(ShipmentStatus, name="shipment_status"), nullable=False, default=ShipmentStatus.PLANNED
    )

    # Timing
    departure_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    eta: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Current position
    current_lat: Mapped[float | None] = mapped_column(Float)
    current_lon: Mapped[float | None] = mapped_column(Float)

    # Cold-chain requirements
    temperature_sensitive: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    min_temperature_c: Mapped[float | None] = mapped_column(Float)
    max_temperature_c: Mapped[float | None] = mapped_column(Float)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    supplier: Mapped["Supplier"] = relationship("Supplier", back_populates="shipments")  # noqa: F821
    route: Mapped["Route | None"] = relationship("Route", back_populates="shipments")  # noqa: F821
    disruption_links: Mapped[list["ShipmentDisruption"]] = relationship(  # noqa: F821
        "ShipmentDisruption", back_populates="shipment", cascade="all, delete-orphan"
    )
    cold_chain_readings: Mapped[list["ColdChainReading"]] = relationship(  # noqa: F821
        "ColdChainReading", back_populates="shipment", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Shipment {self.shipment_code} {self.origin}→{self.destination} {self.status}>"
