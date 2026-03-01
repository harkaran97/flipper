"""
parts_search_result.py

Stores live parts pricing from LinkUp. TTL 24 hours — parts prices change.
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class PartsSearchResult(Base):
    __tablename__ = "parts_search_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    listing_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("listings.id"), nullable=False)
    fault_type: Mapped[str] = mapped_column(String(100), nullable=False)
    part_name: Mapped[str] = mapped_column(String(200), nullable=False)
    supplier: Mapped[str] = mapped_column(String(100), nullable=False)
    price_pence: Mapped[int] = mapped_column(Integer, nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    in_stock: Mapped[bool] = mapped_column(Boolean, default=True)
    searched_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    @property
    def is_fresh(self) -> bool:
        return (datetime.utcnow() - self.searched_at).total_seconds < 86400  # 24h

    def __repr__(self) -> str:
        return f"<PartsSearchResult(listing_id={self.listing_id}, part={self.part_name}, supplier={self.supplier})>"
