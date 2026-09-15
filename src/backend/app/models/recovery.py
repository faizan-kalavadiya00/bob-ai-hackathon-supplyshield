"""RecoveryPlan ORM model."""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class RecoveryPlanStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class RecoveryPlan(Base):
    __tablename__ = "recovery_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    disruption_id: Mapped[int | None] = mapped_column(ForeignKey("disruptions.id"))
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    # Ordered list of recovery steps as JSON array
    steps: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    estimated_recovery_hours: Mapped[float | None] = mapped_column(Float)
    rri_recovery_projected: Mapped[float | None] = mapped_column(Float)
    status: Mapped[RecoveryPlanStatus] = mapped_column(
        Enum(RecoveryPlanStatus, name="recovery_plan_status"),
        nullable=False,
        default=RecoveryPlanStatus.DRAFT,
    )
    created_by: Mapped[str] = mapped_column(String(200), nullable=False, default="system")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<RecoveryPlan {self.id} {self.title} {self.status}>"
