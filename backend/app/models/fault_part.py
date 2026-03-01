"""
fault_part.py

Maps fault types to the parts required to fix them.
Pre-seeded. Manually maintained.
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class FaultPart(Base):
    __tablename__ = "fault_parts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fault_type: Mapped[str] = mapped_column(String(100), nullable=False)
    part_name: Mapped[str] = mapped_column(String(200), nullable=False)
    part_category: Mapped[str] = mapped_column(String(50), nullable=False)
    quantity: Mapped[str] = mapped_column(String(50), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_consumable: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<FaultPart(fault_type={self.fault_type}, part_name={self.part_name})>"
