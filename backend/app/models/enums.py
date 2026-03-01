"""
enums.py — Single source of truth for all enum types.
All models and services import enums from here.
"""
from enum import Enum


class FaultSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class FaultSource(str, Enum):
    AI = "ai"
    KEYWORD = "keyword"
    PRE_SEEDED = "pre_seeded"


class WriteOffCategory(str, Enum):
    CLEAN = "clean"
    CAT_N = "cat_n"           # Non-structural damage (formerly Cat D)
    CAT_S = "cat_s"           # Structural damage (formerly Cat C)
    CAT_A = "cat_a"           # Exclude — cannot be repaired
    CAT_B = "cat_b"           # Exclude — cannot be repaired
    FLOOD = "flood"           # Flood damage flag
    FIRE = "fire"             # Fire damage flag
    UNKNOWN_WRITEOFF = "unknown_writeoff"  # Write-off mentioned but category unclear


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class MarketValueSource(str, Enum):
    EBAY_SOLD = "ebay_sold"
    LINKUP_FALLBACK = "linkup_fallback"


class MarketValueConfidence(str, Enum):
    HIGH = "high"     # >= 5 sold comps
    MEDIUM = "medium"  # 3-4 sold comps
    LOW = "low"       # < 3 sold comps


class ListingSource(str, Enum):
    EBAY = "ebay"
    GUMTREE = "gumtree"
    AUTOTRADER = "autotrader"


class FuelType(str, Enum):
    PETROL = "petrol"
    DIESEL = "diesel"
    HYBRID = "hybrid"
    MILD_HYBRID = "mild_hybrid"
    ELECTRIC = "electric"


class CommonProblemSource(str, Enum):
    PRE_SEEDED = "pre_seeded"
    SYSTEM_OBSERVED = "system_observed"
    LINKUP_CONFIRMED = "linkup_confirmed"
