"""Disruption and ShipmentDisruption ORM models."""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class DisruptionType(str, enum.Enum):
    WEATHER = "weather"
    PORT = "port"
    SUPPLIER = "supplier"
    GEOPOLITICAL = "geopolitical"
    CYBER = "cyber"
    DEMAND = "demand"
    TRANSPORT = "transport"
    REGULATORY = "regulatory"


class DisruptionStatus(str, enum.Enum):
    ACTIVE = "active"
    MONITORING = "monitoring"
    RESOLVED = "resolved"
    HISTORICAL = "historical"


class Disruption(Base):
    __tablename__ = "disruptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    disruption_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    type: Mapped[DisruptionType] = mapped_column(
        Enum(DisruptionType, name="disruption_type"), nullable=False
    )
    # 1 (minor) – 10 (catastrophic)
    severity: Mapped[int] = mapped_column(Integer, nullable=False)
    affected_region: Mapped[str] = mapped_column(String(200), nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[DisruptionStatus] = mapped_column(
        Enum(DisruptionStatus, name="disruption_status"),
        nullable=False,
        default=DisruptionStatus.ACTIVE,
    )
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    shipment_links: Mapped[list["ShipmentDisruption"]] = relationship(
        "ShipmentDisruption", back_populates="disruption", cascade="all, delete-orphan"
    )
    dna: Mapped["DisruptionDNA | None"] = relationship(  # noqa: F821
        "DisruptionDNA", back_populates="disruption", uselist=False,
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Disruption {self.disruption_code} {self.name} sev={self.severity}>"


class ShipmentDisruption(Base):
    """Many-to-many: which disruptions affect which shipments."""

    __tablename__ = "shipment_disruptions"

    shipment_id: Mapped[int] = mapped_column(
        ForeignKey("shipments.id", ondelete="CASCADE"), primary_key=True
    )
    disruption_id: Mapped[int] = mapped_column(
        ForeignKey("disruptions.id", ondelete="CASCADE"), primary_key=True
    )
    # 0.0–1.0 fraction of shipment value at risk
    impact_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    delay_hours: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Relationships
    shipment: Mapped["Shipment"] = relationship("Shipment", back_populates="disruption_links")  # noqa: F821
    disruption: Mapped["Disruption"] = relationship("Disruption", back_populates="shipment_links")

    def __repr__(self) -> str:
        return f"<ShipmentDisruption ship={self.shipment_id} dis={self.disruption_id}>"
