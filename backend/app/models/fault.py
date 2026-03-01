import uuid
from datetime import datetime

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enums import FaultSeverity, FaultSource  # noqa: F401


class DetectedFault(Base):
    __tablename__ = "detected_faults"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    listing_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("listings.id"), nullable=False)
    issue: Mapped[str] = mapped_column(String(255), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False)

    def __repr__(self) -> str:
        return f"<DetectedFault(id={self.id}, issue={self.issue}, severity={self.severity})>"


class FaultCache(Base):
    __tablename__ = "fault_cache"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cache_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    repair_min_pence: Mapped[int] = mapped_column(Integer, nullable=False)
    repair_max_pence: Mapped[int] = mapped_column(Integer, nullable=False)
    repair_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)
    ttl_days: Mapped[int] = mapped_column(Integer, default=30, nullable=False)

    def __repr__(self) -> str:
        return f"<FaultCache(id={self.id}, cache_key={self.cache_key})>"
