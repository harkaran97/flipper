"""
linkup_market_value_cache.py

Caches LinkUp market value results keyed by {make}_{model}_{year}_{write_off_category}.
TTL 30 days. Prevents redundant LinkUp API calls for the same vehicle/category combo.
"""
import uuid
from datetime import datetime

from sqlalchemy import Float, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class LinkupMarketValueCache(Base):
    __tablename__ = "linkup_market_value_cache"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cache_key: Mapped[str] = mapped_column(String(300), unique=True, nullable=False)
    # key format: "{make}_{model}_{year}_{write_off_category}" lowercased
    # e.g. "bmw_3 series_2015_cat_n"
    median_sold_price_gbp: Mapped[float] = mapped_column(Float, nullable=False)
    price_range_low_gbp: Mapped[float] = mapped_column(Float, nullable=False)
    price_range_high_gbp: Mapped[float] = mapped_column(Float, nullable=False)
    sample_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    ttl_days: Mapped[int] = mapped_column(Integer, default=30)

    def __repr__(self) -> str:
        return (
            f"<LinkupMarketValueCache(key={self.cache_key}, "
            f"median=£{self.median_sold_price_gbp:.0f}, created={self.created_at.date()})>"
        )
