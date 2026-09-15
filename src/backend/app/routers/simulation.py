from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.database import get_db
from app.models.simulation import SimulationRun
from app.schemas.simulation import SimulationRunCreate, SimulationRunOut

router = APIRouter(prefix="/api/simulation", tags=["Simulation"])

@router.get("", response_model=List[SimulationRunOut])
async def list_simulations(db: AsyncSession = Depends(get_db)):
    def _work(session: Session):
        return session.scalars(select(SimulationRun).order_by(SimulationRun.created_at.desc())).all()
    
    return await db.run_sync(_work)

@router.get("/{id}", response_model=SimulationRunOut)
async def get_simulation(id: int, db: AsyncSession = Depends(get_db)):
    def _work(session: Session):
        return session.get(SimulationRun, id)
        
    run = await db.run_sync(_work)
    if not run:
        raise HTTPException(status_code=404, detail="Simulation run not found")
    return run

@router.post("", response_model=SimulationRunOut)
async def create_simulation(sim_in: SimulationRunCreate, db: AsyncSession = Depends(get_db)):
    def _work(session: Session):
        # Compute a dummy RRI impact based on some params
        rri_impact = -5.0
        if "severity" in sim_in.parameters:
            severity = sim_in.parameters["severity"]
            if severity == "high":
                rri_impact = -15.0
            elif severity == "medium":
                rri_impact = -10.0
                
        run = SimulationRun(
            scenario_type=sim_in.scenario_type,
            parameters=sim_in.parameters,
            result_summary={"status": "completed", "message": "Simulation executed successfully."},
            rri_impact=rri_impact
        )
        session.add(run)
        session.commit()
        session.refresh(run)
        return run
        
    return await db.run_sync(_work)
