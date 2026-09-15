from datetime import datetime
from pydantic import BaseModel, ConfigDict
from typing import Optional

from app.models.fleet import VehicleStatus

class FleetVehicleBase(BaseModel):
    vehicle_code: str
    vehicle_type: str
    capacity_kg: float
    current_location: str
    current_lat: float
    current_lon: float
    status: VehicleStatus
    available_from: datetime
    refrigerated: bool

class FleetVehicleCreate(FleetVehicleBase):
    pass

class FleetVehicleOut(FleetVehicleBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class RouteBase(BaseModel):
    route_code: str
    route_name: str
    origin: str
    destination: str
    distance_km: float
    duration_hours: float
    risk_score: float
    capacity_kg: float
    is_primary: bool
    transport_mode: str

class RouteCreate(RouteBase):
    pass

class RouteOut(RouteBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class RouteAlternativeOut(RouteOut):
    # This might include additional fields like a computed reason, but we can just use RouteOut for now.
    pass
