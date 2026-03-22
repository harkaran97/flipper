from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class RawListing:
    external_id: str
    source: str
    title: str
    description: str
    price_pence: int
    postcode: str
    url: str
    raw_json: dict


@dataclass
class SoldListing:
    title: str
    sold_price_pence: int
    year: int
    make: str
    model: str


@dataclass
class PartListing:
    title: str
    price_pence: int
    url: str


@dataclass
class SearchResult:
    query: str
    summary: str
    sources: list[str] = None
    structured_data: dict | None = None


class BaseListingsAdapter(ABC):
    @abstractmethod
    async def search_listings(self, query: str, filters: dict) -> list[RawListing]:
        """Search for spares/repair vehicle listings."""


class BaseSoldAdapter(ABC):
    @abstractmethod
    async def search_sold(self, make: str, model: str, year: int) -> list[SoldListing]:
        """Search for completed/sold vehicle listings for price benchmarking."""


class BasePartsAdapter(ABC):
    @abstractmethod
    async def search_parts(self, part_name: str, vehicle: str) -> list[PartListing]:
        """Search for parts by name and vehicle compatibility."""


class BaseSearchAdapter(ABC):
    @abstractmethod
    async def web_search(self, query: str) -> SearchResult:
        """Web search for fault intelligence."""
