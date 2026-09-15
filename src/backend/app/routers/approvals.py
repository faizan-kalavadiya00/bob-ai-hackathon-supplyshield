from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from datetime import datetime, timezone

from app.database import get_db
from app.models.approval import Approval, ApprovalStatus
from app.models.audit import AuditLog
from app.schemas.approval import ApprovalOut

router = APIRouter(prefix="/api/approvals", tags=["Approvals"])

@router.get("", response_model=List[ApprovalOut])
async def list_approvals(
    status: Optional[ApprovalStatus] = Query(None, description="Filter by status"),
    db: AsyncSession = Depends(get_db)
):
    def _work(session: Session):
        stmt = select(Approval).order_by(Approval.requested_at.desc())
        if status:
            stmt = stmt.where(Approval.status == status)
        return list(session.scalars(stmt).all())
    
    return await db.run_sync(_work)

@router.get("/{id}", response_model=ApprovalOut)
async def get_approval(id: int, db: AsyncSession = Depends(get_db)):
    def _work(session: Session):
        return session.get(Approval, id)
        
    approval = await db.run_sync(_work)
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    return approval

@router.post("/{id}/approve", response_model=ApprovalOut)
async def approve_approval(id: int, db: AsyncSession = Depends(get_db)):
    def _work(session: Session):
        approval = session.get(Approval, id)
        if not approval:
            raise HTTPException(status_code=404, detail="Approval not found")
        if approval.status != ApprovalStatus.PENDING:
            raise HTTPException(status_code=400, detail="Approval is not pending")
            
        approval.status = ApprovalStatus.APPROVED
        approval.resolved_at = datetime.now(timezone.utc)
        # Typically would come from auth context
        approval.approved_by = "admin" 
        
        # Write audit log
        audit = AuditLog(
            actor="admin",
            action="approve",
            entity_type="Approval",
            entity_id=str(approval.id),
            before_state={"status": "pending"},
            after_state={"status": "approved"}
        )
        session.add(audit)
        
        session.commit()
        session.refresh(approval)
        return approval
        
    return await db.run_sync(_work)

@router.post("/{id}/reject", response_model=ApprovalOut)
async def reject_approval(id: int, db: AsyncSession = Depends(get_db)):
    def _work(session: Session):
        approval = session.get(Approval, id)
        if not approval:
            raise HTTPException(status_code=404, detail="Approval not found")
        if approval.status != ApprovalStatus.PENDING:
            raise HTTPException(status_code=400, detail="Approval is not pending")
            
        approval.status = ApprovalStatus.REJECTED
        approval.resolved_at = datetime.now(timezone.utc)
        approval.approved_by = "admin" 
        
        # Write audit log
        audit = AuditLog(
            actor="admin",
            action="reject",
            entity_type="Approval",
            entity_id=str(approval.id),
            before_state={"status": "pending"},
            after_state={"status": "rejected"}
        )
        session.add(audit)
        
        session.commit()
        session.refresh(approval)
        return approval
        
    return await db.run_sync(_work)
