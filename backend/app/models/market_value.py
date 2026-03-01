"""
market_value.py

Stores the market value estimate for a listing's vehicle,
derived from sold comps (eBay sold or LinkUp fallback).
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enums import MarketValueConfidence, MarketValueSource  # noqa: F401


class MarketValue(Base):
    __tablename__ = "market_values"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    listing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("listings.id"), unique=True, nullable=False
    )
    write_off_category: Mapped[str] = mapped_column(String(30), nullable=False)
    comp_count: Mapped[int] = mapped_column(Integer, default=0)
    median_value_pence: Mapped[int] = mapped_column(Integer, default=0)
    low_value_pence: Mapped[int] = mapped_column(Integer, default=0)
    high_value_pence: Mapped[int] = mapped_column(Integer, default=0)
    source: Mapped[str] = mapped_column(String(30), nullable=False)
    confidence: Mapped[str] = mapped_column(String(10), nullable=False)
    linkup_fallback_used: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    def __repr__(self) -> str:
        return (
            f"<MarketValue(id={self.id}, median={self.median_value_pence}, "
            f"confidence={self.confidence}, comps={self.comp_count})>"
        )
