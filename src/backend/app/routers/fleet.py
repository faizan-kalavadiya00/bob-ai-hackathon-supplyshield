from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.database import get_db
from app.models.fleet import FleetVehicle
from app.models.route import Route
from app.schemas.fleet import FleetVehicleOut, RouteOut

router = APIRouter(prefix="/api", tags=["Fleet and Routing"])

@router.get("/fleet", response_model=List[FleetVehicleOut])
async def list_fleet(db: AsyncSession = Depends(get_db)):
    def _work(sync_session: Session):
        result = sync_session.execute(select(FleetVehicle).order_by(FleetVehicle.id))
        return result.scalars().all()
    
    return await db.run_sync(_work)

@router.get("/fleet/{id}", response_model=FleetVehicleOut)
async def get_vehicle(id: int, db: AsyncSession = Depends(get_db)):
    def _work(sync_session: Session):
        return sync_session.get(FleetVehicle, id)
    
    vehicle = await db.run_sync(_work)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    return vehicle

@router.get("/routes", response_model=List[RouteOut])
async def list_routes(db: AsyncSession = Depends(get_db)):
    def _work(sync_session: Session):
        result = sync_session.execute(select(Route).order_by(Route.id))
        return result.scalars().all()
    
    return await db.run_sync(_work)

@router.get("/routes/{id}/alternatives", response_model=List[RouteOut])
async def get_route_alternatives(id: int, db: AsyncSession = Depends(get_db)):
    def _work(sync_session: Session):
        route = sync_session.get(Route, id)
        if not route:
            return None
        
        # Return other routes with same origin and destination
        result = sync_session.execute(
            select(Route).where(
                Route.origin == route.origin,
                Route.destination == route.destination,
                Route.id != route.id
            ).order_by(Route.risk_score)
        )
        return result.scalars().all()
        
    alternatives = await db.run_sync(_work)
    if alternatives is None:
        raise HTTPException(status_code=404, detail="Route not found")
    return alternatives
