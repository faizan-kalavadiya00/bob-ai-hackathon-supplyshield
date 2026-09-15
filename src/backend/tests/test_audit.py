import pytest
from httpx import ASGITransport, AsyncClient
from fastapi import FastAPI
from app.routers.audit import router
from app.database import get_db
from app.models.audit import AuditLog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

test_app = FastAPI()
test_app.include_router(router)

@pytest.fixture
async def db_session():
    async for db in get_db():
        yield db

@pytest.fixture
async def sample_audit(db_session: AsyncSession):
    def _work(session: Session):
        audit = AuditLog(
            actor="test_user",
            action="test_action",
            entity_type="TestEntity",
            entity_id="123",
            before_state={"status": "old"},
            after_state={"status": "new"}
        )
        session.add(audit)
        session.commit()
        session.refresh(audit)
        return audit
    return await db_session.run_sync(_work)

@pytest.mark.asyncio
async def test_list_audit_logs(sample_audit):
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        # List all
        response = await client.get("/api/audit")
        assert response.status_code == 200, response.text
        data = response.json()
        assert "items" in data
        assert data["total"] >= 1
        
        # Filter by entity_type
        response = await client.get("/api/audit?entity_type=TestEntity")
        assert response.status_code == 200, response.text
        data = response.json()
        assert len(data["items"]) >= 1
        assert data["items"][0]["entity_type"] == "TestEntity"
        
        # Filter by action
        response = await client.get("/api/audit?action=test_action")
        assert response.status_code == 200, response.text
        data = response.json()
        assert len(data["items"]) >= 1
        assert data["items"][0]["action"] == "test_action"

@pytest.mark.asyncio
async def test_get_audit_log(sample_audit):
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        response = await client.get(f"/api/audit/{sample_audit.id}")
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["id"] == sample_audit.id
        assert data["actor"] == "test_user"
