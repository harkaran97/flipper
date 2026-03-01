import uuid
from datetime import datetime

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enums import RiskLevel  # noqa: F401


class Opportunity(Base):
    __tablename__ = "opportunities"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    listing_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("listings.id"), nullable=False)
    listing_price_pence: Mapped[int] = mapped_column(Integer, nullable=False)
    repair_cost_mid_pence: Mapped[int] = mapped_column(Integer, nullable=False)
    market_value_pence: Mapped[int] = mapped_column(Integer, nullable=False)
    expected_profit_pence: Mapped[int] = mapped_column(Integer, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False)
    alerted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<Opportunity(id={self.id}, profit={self.expected_profit_pence}, score={self.score})>"
