import pytest
from httpx import ASGITransport, AsyncClient
from fastapi import FastAPI
from app.routers.approvals import router as approvals_router
from app.routers.audit import router as audit_router
from app.database import get_db
from app.models.approval import Approval, ApprovalStatus
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from sqlalchemy import text

test_app = FastAPI()
test_app.include_router(approvals_router)
test_app.include_router(audit_router)

@pytest.fixture
async def sample_approval(db_session: AsyncSession):
    def _work(session: Session):
        approval = Approval(
            action_type="test_action",
            payload={"key": "value"},
            requested_by="user1"
        )
        session.add(approval)
        session.commit()
        session.refresh(approval)
        return approval
    return await db_session.run_sync(_work)

@pytest.fixture
async def db_session():
    async for db in get_db():
        yield db

@pytest.mark.asyncio
async def test_list_and_get_approval(sample_approval):
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        # List
        response = await client.get("/api/approvals")
        assert response.status_code == 200, response.text
        data = response.json()
        assert len(data) >= 1
        
        # Filter by status
        response = await client.get("/api/approvals?status=pending")
        assert response.status_code == 200, response.text
        assert len(response.json()) >= 1
        
        # Get specific
        response = await client.get(f"/api/approvals/{sample_approval.id}")
        assert response.status_code == 200, response.text
        assert response.json()["id"] == sample_approval.id
        assert response.json()["action_type"] == "test_action"

@pytest.mark.asyncio
async def test_approve_approval(sample_approval):
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        response = await client.post(f"/api/approvals/{sample_approval.id}/approve")
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["status"] == "approved"
        assert data["approved_by"] == "admin"
        assert data["resolved_at"] is not None

@pytest.mark.asyncio
async def test_reject_approval(db_session):
    def _work(session: Session):
        approval = Approval(
            action_type="test_reject",
            payload={"key": "val"},
            requested_by="user2"
        )
        session.add(approval)
        session.commit()
        session.refresh(approval)
        return approval
        
    approval = await db_session.run_sync(_work)
    
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        response = await client.post(f"/api/approvals/{approval.id}/reject")
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["status"] == "rejected"
        assert data["approved_by"] == "admin"
