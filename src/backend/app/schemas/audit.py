from typing import Any, Dict, Optional, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class AuditLogBase(BaseModel):
    actor: str
    action: str
    entity_type: str
    entity_id: str
    before_state: Optional[Dict[str, Any]] = None
    after_state: Optional[Dict[str, Any]] = None
    source: str = "api"

class AuditLogCreate(AuditLogBase):
    pass

class AuditLogOut(AuditLogBase):
    id: int
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)

class PaginatedAuditLogs(BaseModel):
    items: List[AuditLogOut]
    total: int
    page: int
    size: int
