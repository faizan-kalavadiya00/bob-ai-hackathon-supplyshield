from typing import Any, Dict, Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.models.approval import ApprovalStatus

class ApprovalBase(BaseModel):
    action_type: str
    payload: Dict[str, Any]
    requested_by: str
    notes: Optional[str] = None

class ApprovalCreate(ApprovalBase):
    pass

class ApprovalOut(ApprovalBase):
    id: int
    status: ApprovalStatus
    approved_by: Optional[str] = None
    requested_at: datetime
    resolved_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
