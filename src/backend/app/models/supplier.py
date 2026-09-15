"""Supplier ORM model."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Supplier(Base):
    __tablename__ = "suppliers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    supplier_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    country: Mapped[str] = mapped_column(String(100), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    # 0.0–1.0: historical on-time delivery and quality score
    reliability_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.8)
    lead_time_days: Mapped[int] = mapped_column(Integer, nullable=False, default=7)
    tier: Mapped[int] = mapped_column(Integer, nullable=False, default=1)  # 1=strategic, 2=preferred, 3=spot
    contact_email: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    shipments: Mapped[list["Shipment"]] = relationship(  # noqa: F821
        "Shipment", back_populates="supplier", lazy="select"
    )
    resilience_wallet: Mapped["ResilienceWallet | None"] = relationship(  # noqa: F821
        "ResilienceWallet",
        primaryjoin="and_(ResilienceWallet.owner_id == foreign(Supplier.id), "
                    "ResilienceWallet.owner_type == 'supplier')",
        lazy="select",
        viewonly=True,
    )

    def __repr__(self) -> str:
        return f"<Supplier {self.supplier_code} {self.name}>"
