from typing import Any, Dict, Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class SimulationRunBase(BaseModel):
    scenario_type: str
    parameters: Dict[str, Any] = {}

class SimulationRunCreate(SimulationRunBase):
    pass

class SimulationRunOut(SimulationRunBase):
    id: int
    result_summary: Dict[str, Any]
    rri_impact: Optional[float] = None
    created_by: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
