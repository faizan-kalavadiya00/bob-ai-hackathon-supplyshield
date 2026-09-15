from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional

from app.database import get_db
from app.models.audit import AuditLog
from app.schemas.audit import AuditLogOut, PaginatedAuditLogs

router = APIRouter(prefix="/api/audit", tags=["Audit Log"])

@router.get("", response_model=PaginatedAuditLogs)
async def list_audit_logs(
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    action: Optional[str] = Query(None, description="Filter by action"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    db: AsyncSession = Depends(get_db)
):
    def _work(session: Session):
        stmt = select(AuditLog)
        
        if entity_type:
            stmt = stmt.where(AuditLog.entity_type == entity_type)
        if action:
            stmt = stmt.where(AuditLog.action == action)
            
        total_stmt = select(func.count()).select_from(stmt.subquery())
        total = session.execute(total_stmt).scalar() or 0
        
        stmt = stmt.order_by(AuditLog.timestamp.desc()).offset((page - 1) * size).limit(size)
        items = list(session.scalars(stmt).all())
        
        return {
            "items": items,
            "total": total,
            "page": page,
            "size": size
        }
    
    return await db.run_sync(_work)

@router.get("/{id}", response_model=AuditLogOut)
async def get_audit_log(id: int, db: AsyncSession = Depends(get_db)):
    def _work(session: Session):
        return session.get(AuditLog, id)
        
    audit_log = await db.run_sync(_work)
    if not audit_log:
        raise HTTPException(status_code=404, detail="Audit log not found")
    return audit_log
