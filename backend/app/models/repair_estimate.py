"""
repair_estimate.py

Stores the total repair cost estimate for a listing.
Aggregates parts costs and man days across all detected faults.
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, Float, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class RepairEstimate(Base):
    __tablename__ = "repair_estimates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    listing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("listings.id"), unique=True, nullable=False
    )
    total_parts_min_pence: Mapped[int] = mapped_column(Integer, default=0)
    total_parts_max_pence: Mapped[int] = mapped_column(Integer, default=0)
    total_man_days: Mapped[float] = mapped_column(Float, default=0.0)
    has_unpriced_faults: Mapped[bool] = mapped_column(Boolean, default=False)
    unpriced_fault_types: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    def __repr__(self) -> str:
        return (
            f"<RepairEstimate(id={self.id}, listing_id={self.listing_id}, "
            f"parts_min={self.total_parts_min_pence}, man_days={self.total_man_days})>"
        )
