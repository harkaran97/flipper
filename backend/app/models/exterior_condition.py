"""
exterior_condition.py

Stores exterior/bodywork assessment separate from mechanical faults.
Each facet assessed independently.
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ExteriorCondition(Base):
    __tablename__ = "exterior_conditions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    listing_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("listings.id"), nullable=False)

    # Write-off / damage category
    write_off_category: Mapped[str] = mapped_column(String(30), nullable=False,
                                                     default="clean")  # WriteOffCategory enum

    # Panel damage
    panel_damage_severity: Mapped[str | None] = mapped_column(String(20), nullable=True)
    panel_damage_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Rust
    rust_severity: Mapped[str | None] = mapped_column(String(20), nullable=True)
    rust_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Paint
    paint_severity: Mapped[str | None] = mapped_column(String(20), nullable=True)
    paint_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Glass
    glass_severity: Mapped[str | None] = mapped_column(String(20), nullable=True)
    glass_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Interior
    interior_severity: Mapped[str | None] = mapped_column(String(20), nullable=True)
    interior_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Flood / fire flags (separate from write-off category)
    flood_damage: Mapped[bool] = mapped_column(Boolean, default=False)
    fire_damage: Mapped[bool] = mapped_column(Boolean, default=False)

    # Overall exterior severity
    overall_severity: Mapped[str | None] = mapped_column(String(20), nullable=True)

    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<ExteriorCondition(id={self.id}, listing_id={self.listing_id}, write_off={self.write_off_category})>"
