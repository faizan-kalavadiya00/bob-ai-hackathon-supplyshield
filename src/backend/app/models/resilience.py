"""ResilienceWallet and ResilienceTransaction ORM models."""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class WalletDimension(str, enum.Enum):
    """The four dimensions of resilience capital."""
    TIME = "time"           # hours of buffer / slack
    COST = "cost"           # USD financial buffer
    TEMPERATURE = "temperature"  # °C-hours of cold-chain tolerance remaining
    CAPACITY = "capacity"   # kg of spare logistics capacity


class ResilienceWallet(Base):
    """Per-entity resilience capital across four dimensions."""

    __tablename__ = "resilience_wallets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    # owner can be 'supplier', 'route', 'shipment', 'system'
    owner_type: Mapped[str] = mapped_column(String(50), nullable=False)
    owner_id: Mapped[int] = mapped_column(Integer, nullable=False)
    dimension: Mapped[WalletDimension] = mapped_column(
        Enum(WalletDimension, name="wallet_dimension"), nullable=False
    )
    balance: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    max_balance: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    transactions: Mapped[list["ResilienceTransaction"]] = relationship(
        "ResilienceTransaction", back_populates="wallet", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return (
            f"<ResilienceWallet {self.owner_type}:{self.owner_id} "
            f"{self.dimension} {self.balance}/{self.max_balance}>"
        )


class ResilienceTransaction(Base):
    """Ledger entry for every wallet change."""

    __tablename__ = "resilience_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    wallet_id: Mapped[int] = mapped_column(
        ForeignKey("resilience_wallets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    dimension: Mapped[WalletDimension] = mapped_column(
        Enum(WalletDimension, name="wallet_dimension"), nullable=False
    )
    # Positive = earned; negative = spent
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    reference_id: Mapped[str | None] = mapped_column(String(100))
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text)

    # Relationships
    wallet: Mapped["ResilienceWallet"] = relationship(
        "ResilienceWallet", back_populates="transactions"
    )

    def __repr__(self) -> str:
        return f"<ResilienceTransaction wallet={self.wallet_id} {self.amount:+.2f} {self.reason}>"
