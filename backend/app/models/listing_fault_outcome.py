import uuid
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Integer, Numeric, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base


class ListingFaultOutcome(Base):
    __tablename__ = "listing_fault_outcomes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    listing_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("listings.id", ondelete="CASCADE"), nullable=True)
    make: Mapped[str | None] = mapped_column(String(100), nullable=True)
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mileage: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fuel_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    predicted_fault_type: Mapped[str] = mapped_column(String(100), nullable=False)
    predicted_confidence: Mapped[float | None] = mapped_column(Numeric(4, 3), nullable=True)
    predicted_severity: Mapped[str | None] = mapped_column(String(50), nullable=True)
    ai_overall_confidence: Mapped[float | None] = mapped_column(Numeric(4, 3), nullable=True)
    confirmed: Mapped[bool | None] = mapped_column(Boolean, default=None, nullable=True)
    actual_fault_type: Mapped[str | None] = mapped_column(String(100), default=None, nullable=True)
    confirmed_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), default=None, nullable=True)
    confirmed_by: Mapped[str | None] = mapped_column(String(50), default=None, nullable=True)
    created_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), server_default=func.now())
