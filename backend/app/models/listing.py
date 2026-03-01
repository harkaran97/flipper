import uuid
from datetime import datetime

from sqlalchemy import Boolean, Integer, Text, String
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enums import ListingSource  # noqa: F401


class Listing(Base):
    __tablename__ = "listings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    price_pence: Mapped[int] = mapped_column(Integer, nullable=False)
    postcode: Mapped[str] = mapped_column(String(10), nullable=True)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    raw_json: Mapped[dict] = mapped_column(JSONB, nullable=True)
    processed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<Listing(id={self.id}, source={self.source}, title={self.title[:40]})>"
