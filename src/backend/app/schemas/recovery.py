from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.models.recovery import RecoveryPlanStatus

class RecoveryPlanBase(BaseModel):
    disruption_id: Optional[int] = None
    title: str
    description: Optional[str] = None
    steps: List[Dict[str, Any]] = []
    estimated_recovery_hours: Optional[float] = None
    rri_recovery_projected: Optional[float] = None
    status: RecoveryPlanStatus = RecoveryPlanStatus.DRAFT

class RecoveryPlanCreate(RecoveryPlanBase):
    pass

class RecoveryPlanOut(RecoveryPlanBase):
    id: int
    created_by: str
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
