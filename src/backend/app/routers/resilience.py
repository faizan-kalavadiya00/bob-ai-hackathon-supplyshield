"""Resilience Wallet and RRI API router.

All numerical values come from deterministic Python services.
No LLM is involved in generating resilience scores.

Architecture note:
  The wallet service uses synchronous SQLAlchemy ORM (session.query()).
  The router uses AsyncSession. We bridge via session.run_sync() which
  executes synchronous code on the same underlying connection without
  blocking the event loop.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.disruption import Disruption, ShipmentDisruption
from app.models.resilience import ResilienceTransaction, ResilienceWallet, WalletDimension
from app.models.route import Route
from app.models.rri import RRISnapshot
from app.models.shipment import CargoPriority, Shipment, ShipmentStatus
from app.schemas.resilience import (
    ApplyEventRequest,
    DimensionStateSchema,
    ResilienceResponse,
    RRIExplanationSchema,
    RRISummarySchema,
    TransactionSchema,
    WalletStateSchema,
)
from app.services.resilience_config import DEFAULT_CONFIG
from app.services.rri_calculator import RRIExplanation, RRIStatus, calculate_rri
from app.services.wallet_service import (
    DimensionState,
    WalletState,
    consume_resilience,
    get_wallet_state,
    initialise_shipment_wallets,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/shipments", tags=["Resilience"])

cfg = DEFAULT_CONFIG


# ── Schema converters (pure functions) ────────────────────────────────────────

def _dim_to_schema(ds: DimensionState) -> DimensionStateSchema:
    return DimensionStateSchema(
        dimension=ds.dimension.value,
        maximum_balance=ds.maximum_balance,
        remaining_balance=ds.remaining_balance,
        consumed_balance=ds.consumed_balance,
        utilization_percent=round(ds.utilization_percent, 2),
        dimension_score=ds.dimension_score,
        status=ds.status(cfg).value,
        unit=ds.unit,
    )


def _wallet_to_schema(ws: WalletState) -> WalletStateSchema:
    return WalletStateSchema(
        shipment_id=ws.shipment_id,
        shipment_code=ws.shipment_code,
        time=_dim_to_schema(ws.time),
        cost=_dim_to_schema(ws.cost),
        temperature=_dim_to_schema(ws.temperature),
        capacity=_dim_to_schema(ws.capacity),
        is_resilience_bankrupt=ws.is_resilience_bankrupt(cfg),
        computed_at=ws.computed_at,
    )


def _rri_to_schema(exp: RRIExplanation) -> RRIExplanationSchema:
    from dataclasses import asdict
    d = {
        "rri": exp.rri,
        "status": exp.status.value,
        "dimensions": exp.dimensions,
        "weights": exp.weights,
        "weighted_scores": exp.weighted_scores,
        "contributors": exp.contributors,
        "criticality_adjustment": exp.criticality_adjustment,
        "weighted_score_before_adjustment": exp.weighted_score_before_adjustment,
        "bankruptcy_flags": exp.bankruptcy_flags,
        "is_resilience_bankrupt": exp.is_resilience_bankrupt,
        "shipment_priority": exp.shipment_priority,
        "computed_at": exp.computed_at,
    }
    return RRIExplanationSchema(**d)


# ── Sync helpers (run inside run_sync) ────────────────────────────────────────

def _load_ship_with_route(sync_session: Session, shipment_id: int) -> Shipment | None:
    ship = sync_session.get(Shipment, shipment_id)
    if ship is None:
        return None
    if ship.route_id:
        ship.route = sync_session.get(Route, ship.route_id)
    return ship


def _compute_resilience(sync_session: Session, ship: Shipment) -> tuple[WalletState, RRIExplanation]:
    ws = get_wallet_state(sync_session, ship, cfg)
    exp = calculate_rri(ws, ship.priority, cfg)
    return ws, exp


def _save_snapshot(sync_session: Session, ship_id: int, exp: RRIExplanation) -> None:
    snap = RRISnapshot(
        entity_type="shipment",
        entity_id=ship_id,
        rri_value=exp.rri / 100.0,
        component_scores={
            "dimensions": exp.dimensions,
            "weights": exp.weights,
            "weighted_scores": exp.weighted_scores,
            "status": exp.status.value,
            "is_resilience_bankrupt": exp.is_resilience_bankrupt,
        },
    )
    sync_session.add(snap)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get(
    "/resilience/summary",
    response_model=RRISummarySchema,
    tags=["Dashboard"],
    summary="Aggregate RRI summary across all active shipments",
)
async def get_resilience_summary(
    db: AsyncSession = Depends(get_db),
) -> RRISummarySchema:
    """Compute the real, deterministic resilience posture for active shipments."""
    def _work(sync_session: Session):
        shipments = (
            sync_session.query(Shipment)
            .filter(Shipment.status.in_([
                ShipmentStatus.IN_TRANSIT,
                ShipmentStatus.AT_RISK,
                ShipmentStatus.DELAYED,
                ShipmentStatus.PLANNED,
            ]))
            .all()
        )
        if not shipments:
            return None

        counts = {"HEALTHY": 0, "STRESSED": 0, "VULNERABLE": 0, "CRITICAL": 0, "BANKRUPT": 0}
        rri_total = 0.0
        bankruptcies = 0
        for ship in shipments:
            if ship.route_id:
                ship.route = sync_session.get(Route, ship.route_id)
            ws = get_wallet_state(sync_session, ship, cfg)
            exp = calculate_rri(ws, ship.priority, cfg)
            counts[exp.status.value] = counts.get(exp.status.value, 0) + 1
            rri_total += exp.rri
            bankruptcies += int(exp.is_resilience_bankrupt)
        return len(shipments), counts, rri_total, bankruptcies

    result = await db.run_sync(_work)
    if result is None:
        return RRISummarySchema(
            total_shipments_assessed=0, average_rri=0.0,
            healthy_count=0, stressed_count=0, vulnerable_count=0,
            critical_count=0, bankrupt_count=0, resilience_bankruptcies=0,
            computed_at=datetime.now(timezone.utc),
        )
    n, counts, rri_total, bankruptcies = result
    return RRISummarySchema(
        total_shipments_assessed=n, average_rri=round(rri_total / n, 2),
        healthy_count=counts.get("HEALTHY", 0), stressed_count=counts.get("STRESSED", 0),
        vulnerable_count=counts.get("VULNERABLE", 0), critical_count=counts.get("CRITICAL", 0),
        bankrupt_count=counts.get("BANKRUPT", 0), resilience_bankruptcies=bankruptcies,
        computed_at=datetime.now(timezone.utc),
    )

@router.get(
    "/{shipment_id}/resilience",
    response_model=ResilienceResponse,
    summary="Get resilience wallet and RRI for a shipment",
)
async def get_shipment_resilience(
    shipment_id: int,
    db: AsyncSession = Depends(get_db),
) -> ResilienceResponse:
    """
    Return the current resilience wallet state and RRI for a shipment.
    All values are calculated deterministically from the database.
    """
    def _work(sync_session: Session):
        ship = _load_ship_with_route(sync_session, shipment_id)
        if ship is None:
            return None
        return _compute_resilience(sync_session, ship)

    result = await db.run_sync(_work)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Shipment {shipment_id} not found")
    ws, exp = result
    return ResilienceResponse(wallet=_wallet_to_schema(ws), rri=_rri_to_schema(exp))


@router.post(
    "/{shipment_id}/resilience/recalculate",
    response_model=ResilienceResponse,
    summary="Recalculate wallet and RRI from current database state",
)
async def recalculate_resilience(
    shipment_id: int,
    db: AsyncSession = Depends(get_db),
) -> ResilienceResponse:
    """Recalculate and persist an RRI snapshot."""
    def _work(sync_session: Session):
        ship = _load_ship_with_route(sync_session, shipment_id)
        if ship is None:
            return None
        ws, exp = _compute_resilience(sync_session, ship)
        _save_snapshot(sync_session, ship.id, exp)
        return ws, exp

    result = await db.run_sync(_work)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Shipment {shipment_id} not found")
    ws, exp = result
    await db.commit()
    logger.info(
        "Recalculated RRI for shipment %d: %.1f (%s)", shipment_id, exp.rri, exp.status.value
    )
    return ResilienceResponse(wallet=_wallet_to_schema(ws), rri=_rri_to_schema(exp))


@router.post(
    "/{shipment_id}/resilience/apply-event",
    response_model=ResilienceResponse,
    status_code=status.HTTP_200_OK,
    summary="Apply a deterministic resilience consumption event",
)
async def apply_resilience_event(
    shipment_id: int,
    event: ApplyEventRequest,
    db: AsyncSession = Depends(get_db),
) -> ResilienceResponse:
    """
    Consume resilience from a specific wallet dimension.
    Creates a ResilienceTransaction record for every debit.
    Balance is clamped at 0.
    """
    dim = WalletDimension(event.dimension)

    def _work(sync_session: Session):
        ship = _load_ship_with_route(sync_session, shipment_id)
        if ship is None:
            return None
        wallets = initialise_shipment_wallets(sync_session, ship, cfg)
        wallet = wallets.get(dim)
        if wallet is None:
            raise ValueError(f"Dimension {event.dimension} wallet not found")
        consume_resilience(
            sync_session, wallet, event.amount, event.reason, event.reference_id
        )
        ws = get_wallet_state(sync_session, ship, cfg)
        exp = calculate_rri(ws, ship.priority, cfg)
        return ws, exp

    result = await db.run_sync(_work)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Shipment {shipment_id} not found")
    ws, exp = result
    await db.commit()
    return ResilienceResponse(wallet=_wallet_to_schema(ws), rri=_rri_to_schema(exp))


@router.get(
    "/{shipment_id}/resilience/transactions",
    response_model=list[TransactionSchema],
    summary="List all resilience transactions for a shipment",
)
async def list_resilience_transactions(
    shipment_id: int,
    db: AsyncSession = Depends(get_db),
) -> list[TransactionSchema]:
    # Verify shipment exists
    result = await db.execute(select(Shipment).where(Shipment.id == shipment_id))
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail=f"Shipment {shipment_id} not found")

    def _load_txs(sync_session: Session) -> list[ResilienceTransaction]:
        return (
            sync_session.query(ResilienceTransaction)
            .join(ResilienceWallet)
            .filter(
                ResilienceWallet.owner_type == "shipment",
                ResilienceWallet.owner_id == shipment_id,
            )
            .order_by(ResilienceTransaction.timestamp.desc())
            .all()
        )

    txs = await db.run_sync(_load_txs)
    return [TransactionSchema.model_validate(tx) for tx in txs]
