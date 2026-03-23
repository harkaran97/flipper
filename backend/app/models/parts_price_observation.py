"""
parts_price_observation.py

Stores every real parts price retrieved from the eBay Parts API.
Accumulates over time to build historical price intelligence.
Never expires — permanent record, not a cache.

One row per (part_name_normalised, make, model, year, supplier, condition, observed_date).
Duplicate writes on the same day are skipped.
"""
import uuid
from datetime import date, datetime

from sqlalchemy import Date, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class PartsPriceObservation(Base):
    __tablename__ = "parts_price_observations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Part identity
    part_name: Mapped[str] = mapped_column(String(200), nullable=False)
    part_name_normalised: Mapped[str] = mapped_column(String(200), nullable=False)
    # normalised = lowercase, alphanumeric + spaces only
    # e.g. "Clutch Kit (3-piece)" → "clutch kit 3piece"

    # Vehicle — exact year, no bands
    make: Mapped[str] = mapped_column(String(100), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)

    # Price — all pence
    supplier: Mapped[str] = mapped_column(String(100), nullable=False)
    condition: Mapped[str] = mapped_column(String(30), nullable=False)
    # "new" | "reconditioned" | "used"
    base_price_pence: Mapped[int] = mapped_column(Integer, nullable=False)
    delivery_pence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_cost_pence: Mapped[int] = mapped_column(Integer, nullable=False)

    # Source tracking
    search_method: Mapped[str] = mapped_column(String(30), nullable=False)
    # "compatibility" | "keyword"
    ebay_item_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Temporal
    observed_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    def __repr__(self) -> str:
        return (
            f"<PartsPriceObservation("
            f"{self.part_name_normalised}, "
            f"{self.make} {self.model} {self.year}, "
            f"£{self.total_cost_pence / 100:.2f} @ {self.supplier})>"
        )
