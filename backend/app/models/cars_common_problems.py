"""
cars_common_problems.py

Cross table linking cars to their known common problems.
Repair costs live here because cost is car-specific.
Populated via pre-seeding AND system observation.
"""
import uuid
from datetime import datetime

from sqlalchemy import Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class CarsCommonProblem(Base):
    __tablename__ = "cars_common_problems"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    car_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("cars.id"), nullable=False)
    problem_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("common_problems.id"), nullable=False)
    repair_parts_min_pence: Mapped[int] = mapped_column(Integer, nullable=False)
    repair_parts_max_pence: Mapped[int] = mapped_column(Integer, nullable=False)
    labour_days_override: Mapped[float | None] = mapped_column(Float, nullable=True)
    occurrence_count: Mapped[int] = mapped_column(Integer, default=1)
    source: Mapped[str] = mapped_column(String(30), nullable=False)  # CommonProblemSource enum
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('car_id', 'problem_id', name='uq_car_problem'),
    )

    def __repr__(self) -> str:
        return f"<CarsCommonProblem(id={self.id}, car_id={self.car_id}, problem_id={self.problem_id})>"
