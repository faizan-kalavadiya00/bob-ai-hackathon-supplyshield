from datetime import datetime
from pydantic import BaseModel, ConfigDict
from typing import Optional, List

class ColdChainReadingBase(BaseModel):
    sensor_id: str
    temperature_c: float
    humidity_pct: Optional[float] = None
    recorded_at: datetime
    is_breach: bool

class ColdChainReadingOut(ColdChainReadingBase):
    id: int
    shipment_id: int
    model_config = ConfigDict(from_attributes=True)

class ColdChainShipmentSummary(BaseModel):
    shipment_id: int
    shipment_code: str
    temperature_sensitive: bool
    min_temperature_c: Optional[float]
    max_temperature_c: Optional[float]
    has_active_breach: bool
    reading_count: int

class ColdChainShipmentDetail(ColdChainShipmentSummary):
    readings: List[ColdChainReadingOut]
