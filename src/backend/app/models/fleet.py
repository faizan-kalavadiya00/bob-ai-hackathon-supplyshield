"""FleetVehicle ORM model."""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class VehicleStatus(str, enum.Enum):
    AVAILABLE = "available"
    IN_TRANSIT = "in_transit"
    MAINTENANCE = "maintenance"
    RESERVED = "reserved"


class FleetVehicle(Base):
    __tablename__ = "fleet_vehicles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    vehicle_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    vehicle_type: Mapped[str] = mapped_column(String(50), nullable=False)
    capacity_kg: Mapped[float] = mapped_column(Float, nullable=False)
    current_location: Mapped[str] = mapped_column(String(200), nullable=False)
    current_lat: Mapped[float] = mapped_column(Float, nullable=False)
    current_lon: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[VehicleStatus] = mapped_column(
        Enum(VehicleStatus, name="vehicle_status"), nullable=False, default=VehicleStatus.AVAILABLE
    )
    available_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    refrigerated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<FleetVehicle {self.vehicle_code} {self.vehicle_type} {self.status}>"
