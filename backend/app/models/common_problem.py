"""
common_problem.py

Master reference table of fault types.
Generic — not tied to any specific car.
Costs are NOT stored here (costs are car-specific, stored in cars_common_problems).
"""
import uuid
from datetime import datetime

from sqlalchemy import Float, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class CommonProblem(Base):
    __tablename__ = "common_problems"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fault_type: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)  # FaultSeverity enum
    description: Mapped[str] = mapped_column(Text, nullable=False)
    labour_days_default: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<CommonProblem(id={self.id}, fault_type={self.fault_type})>"
