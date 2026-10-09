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
    display_name: str = ""           # "Timing chain"
    severity: str
    description: str | None          # generic, from common_problems
    explanation: str | None = None   # plain English, about THIS car (AI)
    seller_quote: str | None = None  # the seller's exact words (AI evidence)
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

    # Display (TASK_040)
    vehicle_name: str = ""           # "2015 Volkswagen Golf R"
    image_url: str | None = None     # first photo, upscaled
    mileage: int | None = None
    location: str | None = None      # town, else outward postcode
    distance_miles: int | None = None
    listed_at: str | None = None     # ISO8601
    fault_names: list[str] = []      # max 3, most severe first
    fix_cost_pence: int = 0          # parts mid + labour: market − price − fix == profit
    profit_is_best_case: bool = False  # no fault detected: profit assumes nothing else is wrong

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

    # User actions
    saved: bool = False
    marked_as_build: bool = False


class OpportunityDetail(BaseModel):
    # Everything in OpportunityCard
    id: str
    listing_id: str
    title: str
    make: str
    model: str
    year: int | None
    listing_url: str
    # Display (TASK_040)
    vehicle_name: str = ""           # "2015 Volkswagen Golf R"
    image_url: str | None = None     # first photo, upscaled
    mileage: int | None = None
    location: str | None = None      # town, else outward postcode
    distance_miles: int | None = None
    listed_at: str | None = None     # ISO8601
    fault_names: list[str] = []      # max 3, most severe first
    fix_cost_pence: int = 0          # parts mid + labour: market − price − fix == profit
    profit_is_best_case: bool = False  # no fault detected: profit assumes nothing else is wrong
    image_urls: list[str] = []
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

    # User actions
    saved: bool = False
    marked_as_build: bool = False

    # Detail-only fields
    faults: list[FaultDetail]
    parts_breakdown: list[FaultPartsBreakdown]
    effort_cost_pence: int
    day_rate_pence: int
    linkup_fallback_used: bool
    sold_comp_urls: list[str] = []


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
