"""Approval ORM model."""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ApprovalStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class Approval(Base):
    __tablename__ = "approvals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    action_type: Mapped[str] = mapped_column(String(100), nullable=False)
    # Full description of what will be executed if approved
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    requested_by: Mapped[str] = mapped_column(String(200), nullable=False)
    approved_by: Mapped[str | None] = mapped_column(String(200))
    status: Mapped[ApprovalStatus] = mapped_column(
        Enum(ApprovalStatus, name="approval_status"),
        nullable=False,
        default=ApprovalStatus.PENDING,
    )
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)

    def __repr__(self) -> str:
        return f"<Approval {self.id} {self.action_type} {self.status}>"
