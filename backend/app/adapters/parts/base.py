"""
base.py

Abstract base class for all parts pricing adapters.
Each supplier (eBay, Autodoc, GSF, etc.) implements this interface.
Failures are always silent — return empty list, log warning.
"""
from abc import ABC, abstractmethod

from app.schemas.parts_pricing import PartResult


class BasePartsSupplierAdapter(ABC):
    """Interface every parts supplier adapter must implement."""

    @abstractmethod
    async def search(
        self,
        part_name: str,
        make: str,
        model: str,
        year: int,
    ) -> list[PartResult]:
        """
        Search for a part from this supplier.
        Returns sorted list of PartResult (cheapest first).
        Must return empty list on any failure — never raise.
        """
