"""
user_settings.py

Single row for personal use. Structured for multi-user later.
Stores user preferences: day rate, budget, location.
"""
import uuid
from datetime import datetime

from sqlalchemy import Float, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class UserSettings(Base):
    __tablename__ = "user_settings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    day_rate_pence: Mapped[int] = mapped_column(Integer, default=15000)  # £150/day
    min_profit_margin_pct: Mapped[float] = mapped_column(Float, default=20.0)
    max_budget_pence: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_man_days: Mapped[float | None] = mapped_column(Float, nullable=True)
    distance_radius_miles: Mapped[int | None] = mapped_column(Integer, nullable=True)
    home_postcode: Mapped[str] = mapped_column(String(10), default="LE4")
    home_lat: Mapped[float] = mapped_column(Float, default=52.6450)
    home_lng: Mapped[float] = mapped_column(Float, default=-1.1237)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<UserSettings(id={self.id}, day_rate_pence={self.day_rate_pence})>"
