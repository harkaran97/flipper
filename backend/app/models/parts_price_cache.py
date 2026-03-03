"""
parts_price_cache.py

Caches multi-source parts pricing results keyed by (part_name, make, model, year_band).
TTL 24 hours. Prevents re-scraping for the same part+vehicle combination.
"""
import uuid
from datetime import datetime

from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class PartsPriceCache(Base):
    __tablename__ = "parts_price_cache"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cache_key: Mapped[str] = mapped_column(String(300), unique=True, nullable=False)
    # key format: "{part_name_slug}_{make}_{model}_{year_band}"
    # e.g. "clutch_kit_bmw_320d_2010s"
    results_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    expires_at: Mapped[datetime] = mapped_column(nullable=False)

    @property
    def is_valid(self) -> bool:
        """Returns True if the cache entry has not expired."""
        return datetime.utcnow() < self.expires_at

    def __repr__(self) -> str:
        return f"<PartsPriceCache(key={self.cache_key}, expires={self.expires_at})>"
