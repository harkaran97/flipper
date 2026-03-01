"""
opportunity.py

Stores the final opportunity assessment for a listing.
Produced by opportunity_scorer after all pipeline steps have completed.
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enums import OpportunityClass, RiskLevel  # noqa: F401


class Opportunity(Base):
    __tablename__ = "opportunities"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    listing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("listings.id"), unique=True, nullable=False
    )

    # Core financials — all pence
    listing_price_pence: Mapped[int] = mapped_column(Integer, nullable=False)
    parts_cost_min_pence: Mapped[int] = mapped_column(Integer, default=0)
    parts_cost_max_pence: Mapped[int] = mapped_column(Integer, default=0)
    parts_cost_mid_pence: Mapped[int] = mapped_column(Integer, default=0)
    effort_cost_pence: Mapped[int] = mapped_column(Integer, default=0)
    market_value_pence: Mapped[int] = mapped_column(Integer, default=0)
    true_profit_pence: Mapped[int] = mapped_column(Integer, default=0)
    true_margin_pct: Mapped[float] = mapped_column(Float, default=0.0)

    # Effort
    total_man_days: Mapped[float] = mapped_column(Float, default=0.0)
    day_rate_pence: Mapped[int] = mapped_column(Integer, default=15000)

    # Classification
    opportunity_class: Mapped[str] = mapped_column(String(20), nullable=False)
    risk_level: Mapped[str] = mapped_column(String(10), nullable=False)

    # Data quality flags
    has_unpriced_faults: Mapped[bool] = mapped_column(Boolean, default=False)
    unpriced_fault_types: Mapped[list] = mapped_column(JSON, default=list)
    market_value_confidence: Mapped[str] = mapped_column(String(10), nullable=False)
    market_value_comp_count: Mapped[int] = mapped_column(Integer, default=0)
    profit_is_floor_estimate: Mapped[bool] = mapped_column(Boolean, default=False)

    # Write-off
    write_off_category: Mapped[str] = mapped_column(
        String(30), nullable=False, default="clean"
    )

    # Alert
    alerted: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self) -> str:
        return (
            f"<Opportunity(id={self.id}, class={self.opportunity_class}, "
            f"profit=£{self.true_profit_pence // 100}, margin={self.true_margin_pct:.1f}%)>"
        )
