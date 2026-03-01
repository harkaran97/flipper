"""
car.py

Vehicle reference table.
Represents a make/model/year_range/engine combination.
Populated by the system as new vehicles are encountered.
Can also be pre-seeded.
"""
import uuid

from sqlalchemy import Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Car(Base):
    __tablename__ = "cars"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    make: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    year_from: Mapped[int] = mapped_column(Integer, nullable=False)
    year_to: Mapped[int] = mapped_column(Integer, nullable=False)
    engine_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    fuel_type: Mapped[str | None] = mapped_column(String(20), nullable=True)  # FuelType enum

    __table_args__ = (
        UniqueConstraint('make', 'model', 'year_from', 'year_to', 'engine_code',
                         name='uq_car_identity'),
    )

    def __repr__(self) -> str:
        return f"<Car(id={self.id}, make={self.make}, model={self.model})>"
