"""
schemas.py

Pydantic response models for the Flipper REST API.
All prices are in pence (GBP). Display conversion happens in the iOS client.
"""
from __future__ import annotations

from pydantic import BaseModel


class SupplierPrice(BaseModel):
    supplier: str
    supplier_logo_key: str = ""
    price_pence: int
    delivery_pence: int = 0
    total_cost_pence: int = 0
    condition: str = "new"
    url: str
    in_stock: bool
    price_confidence: str = "live"


class PartResult(BaseModel):
    part_name: str
    part_category: str
    quantity: str
    is_consumable: bool
    suppliers: list[SupplierPrice]
    cheapest_pence: int | None = None


class FaultDetail(BaseModel):
    fault_type: str
    severity: str
    description: str | None
    labour_days: float


class FaultPartsBreakdown(BaseModel):
    fault_type: str
    parts: list[PartResult]
    fault_parts_total_min_pence: int
    fault_parts_total_max_pence: int


class OpportunityCard(BaseModel):
    id: str
    listing_id: str

    # Vehicle
    title: str
    make: str
    model: str
    year: int | None
    listing_url: str

    # Financials
    listing_price_pence: int
    parts_cost_min_pence: int
    parts_cost_max_pence: int
    market_value_pence: int
    true_profit_pence: int
    true_margin_pct: float

    # Effort
    total_man_days: float

    # Classification
    opportunity_class: str  # strong / speculative / worth_a_look
    risk_level: str         # low / medium / high
    write_off_category: str

    # Data quality
    has_unpriced_faults: bool
    profit_is_floor_estimate: bool
    market_value_confidence: str
    market_value_comp_count: int

    created_at: str  # ISO8601


class OpportunityDetail(BaseModel):
    # Everything in OpportunityCard
    id: str
    listing_id: str
    title: str
    make: str
    model: str
    year: int | None
    listing_url: str
    listing_price_pence: int
    parts_cost_min_pence: int
    parts_cost_max_pence: int
    market_value_pence: int
    true_profit_pence: int
    true_margin_pct: float
    total_man_days: float
    opportunity_class: str
    risk_level: str
    write_off_category: str
    has_unpriced_faults: bool
    unpriced_fault_types: list[str]
    profit_is_floor_estimate: bool
    market_value_confidence: str
    market_value_comp_count: int
    created_at: str

    # Detail-only fields
    faults: list[FaultDetail]
    parts_breakdown: list[FaultPartsBreakdown]
    effort_cost_pence: int
    day_rate_pence: int
    linkup_fallback_used: bool


class OpportunityFeedResponse(BaseModel):
    opportunities: list[OpportunityCard]
    total: int
    has_more: bool


class RefreshResponse(BaseModel):
    job_id: str
    status: str  # pending / running / complete / failed


class RefreshStatusResponse(BaseModel):
    job_id: str
    status: str
    started_at: str | None
    completed_at: str | None
    listings_found: int | None
    error: str | None
