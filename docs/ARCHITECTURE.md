# Flipper — Backend Architecture

> **This document is the single source of truth for all engineering decisions.**
> Claude Code must read this before every task and update it after every milestone.

---

## 1. Product Summary

Flipper is an iOS application that helps car flippers find, evaluate, and act on
spares-or-repair vehicle opportunities. It monitors listings, detects faults using AI,
estimates repair costs, benchmarks market value, and scores profit potential — delivering
high-signal alerts to the user.

**Current user:** Single end-user (personal use, UK market)
**Design constraint:** Extreme simplicity. Every feature must justify its complexity cost.

---

## 2. Core Principles

1. **Iterative over complete** — ship working slices, extend via events
2. **Adapters over assumptions** — every external data source is behind an interface
3. **Stubs are first-class** — all adapters run in stub mode before going live
4. **AI is gated** — LLM calls only fire after keyword pre-filtering; always cached
5. **One service** — no microservices; single Python backend process
6. **Cost-conscious** — every AI/API call must justify its cost with a cache-first policy

---

## 3. Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11+ |
| API Framework | FastAPI |
| Database | PostgreSQL |
| ORM | SQLAlchemy (async) |
| Background Workers | asyncio-based, independently runnable |
| Event Bus | Internal in-process event system (no Kafka/Redis for MVP) |
| AI Layer | Anthropic Claude API (via single `ai_service` module) |
| Web Search | LinkUp API (via single `search_service` module) |
| Hosting | Railway (MVP) |
| Mobile Client | iOS SwiftUI |

---

## 4. Repository Structure

```
flipper/
│
├── docs/
│   ├── PRD.md
│   ├── ARCHITECTURE.md          ← this file
│   └── tasks/                   ← Claude Code task specs (read-only reference)
│
├── backend/
│   ├── main.py                  ← FastAPI app entry point
│   ├── config.py                ← All env vars and settings
│   │
│   ├── app/
│   │   ├── api/                 ← HTTP route handlers
│   │   │   ├── opportunities.py
│   │   │   └── health.py
│   │   │
│   │   ├── models/              ← SQLAlchemy DB models only (no logic)
│   │   │   ├── base.py
│   │   │   ├── listing.py
│   │   │   ├── vehicle.py
│   │   │   ├── fault.py
│   │   │   ├── repair_estimate.py
│   │   │   └── opportunity.py
│   │   │
│   │   ├── adapters/            ← All external data source integrations
│   │   │   ├── base.py          ← Abstract base classes (interfaces)
│   │   │   ├── ebay/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── client.py    ← eBay API auth + HTTP client
│   │   │   │   ├── listings.py  ← search_listings() implementation
│   │   │   │   ├── sold.py      ← search_sold() implementation
│   │   │   │   ├── parts.py     ← search_parts() implementation
│   │   │   │   └── stub.py      ← Stub implementations (used when EBAY_STUB=true)
│   │   │   └── linkup/
│   │   │       ├── __init__.py
│   │   │       ├── client.py    ← LinkUp API client
│   │   │       ├── search.py    ← web_search() implementation
│   │   │       └── stub.py      ← Stub implementation
│   │   │
│   │   ├── services/            ← Business logic (pure functions, no DB access)
│   │   │   ├── ai_service.py    ← ALL AI calls go through here
│   │   │   ├── search_service.py← ALL LinkUp calls go through here
│   │   │   ├── problem_detector.py
│   │   │   ├── repair_estimator.py
│   │   │   ├── market_valuator.py
│   │   │   └── opportunity_scorer.py
│   │   │
│   │   ├── workers/             ← Background pipeline workers
│   │   │   ├── ingestion_worker.py
│   │   │   ├── enrichment_worker.py
│   │   │   ├── detection_worker.py
│   │   │   ├── estimation_worker.py
│   │   │   └── scoring_worker.py
│   │   │
│   │   ├── events/
│   │   │   ├── __init__.py
│   │   │   ├── bus.py           ← In-process event bus
│   │   │   └── types.py         ← Event type definitions
│   │   │
│   │   └── core/
│   │       ├── database.py      ← Async DB session management
│   │       └── logging.py       ← Structured logging setup
│   │
│   └── migrations/              ← Alembic migration files
│
├── tests/
│   ├── smoke/                   ← Smoke tests (run after each task)
│   └── unit/
│
└── README.md
```

---

## 5. Adapter Pattern (Critical — Read Before Building)

Every external data source implements the abstract interface in `adapters/base.py`.
This is the most important architectural decision. It means:

- Swapping eBay for AutoTrader = write a new adapter, zero pipeline changes
- Testing without live APIs = set `EBAY_STUB=true` in env
- Adding Gumtree in Phase 3 = add `adapters/gumtree/`

### Base interfaces (defined in `adapters/base.py`):

```python
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
```

### Stub toggle:
```
EBAY_STUB=true    → uses adapters/ebay/stub.py
LINKUP_STUB=true  → uses adapters/linkup/stub.py
```

Both stubs return realistic hardcoded data matching the interface contract exactly.

---

## 6. Event System

All pipeline steps communicate via domain events. The bus is in-process (no Redis/Kafka).

### Event flow:

```
NEW_LISTING_FOUND
    → VEHICLE_ENRICHED
        → PROBLEMS_DETECTED
            → REPAIR_ESTIMATED
                → MARKET_VALUE_ESTIMATED
                    → OPPORTUNITY_CREATED
```

### Event bus contract:
- `bus.emit(event_type, payload)` — fire and forget
- `bus.subscribe(event_type, handler)` — register a handler
- Handlers are async functions
- Failed handlers log errors and do NOT crash the pipeline

---

## 7. AI Service (`services/ai_service.py`)

**All LLM calls go through this module. No exceptions.**

### Cost controls (mandatory):
1. **Pre-filter gate** — listings only reach AI if they contain trigger keywords:
   `["spares", "repair", "non-runner", "fault", "issue", "damage", "blown",
    "seized", "knocking", "smoking", "misfire", "gearbox", "clutch", "timing"]`

2. **Fault cache** — results keyed by `(make, model, year_band, fault_type)`.
   Cache hit = no LLM call. Cache stored in DB (`fault_cache` table).

3. **Model:** `claude-haiku-3` for classification tasks, `claude-sonnet` only for
   complex multi-fault analysis.

4. **Max tokens:** 512 for fault detection, 256 for repair estimates.

### Primary prompt (problem detection):
```
You are an expert UK automotive mechanic.
Given this vehicle listing, identify likely mechanical faults.

Vehicle: {make} {model} {year}
Listing: {title}. {description}

Return JSON only:
{
  "issues": ["<fault_1>", "<fault_2>"],
  "driveable": true|false,
  "confidence": 0.0-1.0,
  "severity": "low|medium|high"
}
```

---

## 8. Search Service (`services/search_service.py`)

**All LinkUp calls go through this module. No exceptions.**

### When LinkUp fires:
- **Fault intelligence:** When a novel fault is detected (not in fault cache)
  → search `"{make} {model} {fault} common fault cost UK"`
  → store result in fault cache
  → never search same fault+model combo twice

- **Market value fallback:** When eBay sold comps < 3 results
  → search `"{make} {model} {year} value UK sold price"`
  → used as supplementary signal only

### LinkUp is NEVER called:
- For opportunity discovery (eBay handles this)
- For parts pricing primary lookup (eBay handles this)
- For any listing where fault is already in cache

---

## 9. Database Schema

### `listings`
| Column | Type | Notes |
|---|---|---|
| id | UUID | PK |
| source | varchar | "ebay", "gumtree" etc |
| external_id | varchar | eBay item ID (unique per source) |
| title | text | |
| description | text | |
| price_pence | int | Store pence, display pounds |
| postcode | varchar | |
| url | text | |
| raw_json | jsonb | Full API response stored |
| processed | bool | Has this entered the pipeline |
| created_at | timestamp | |

### `vehicles`
| Column | Type | Notes |
|---|---|---|
| id | UUID | PK |
| listing_id | UUID | FK → listings |
| make | varchar | |
| model | varchar | |
| year | int | |
| engine_cc | int | nullable |
| fuel_type | varchar | nullable |
| transmission | varchar | nullable |

### `detected_faults`
| Column | Type | Notes |
|---|---|---|
| id | UUID | PK |
| listing_id | UUID | FK → listings |
| issue | varchar | Normalised fault name |
| confidence | float | 0.0–1.0 |
| severity | varchar | low/medium/high |
| source | varchar | "ai" or "keyword" |

### `fault_cache`
| Column | Type | Notes |
|---|---|---|
| id | UUID | PK |
| cache_key | varchar | UNIQUE: `{make}_{model}_{year_band}_{fault}` |
| repair_min_pence | int | |
| repair_max_pence | int | |
| repair_notes | text | From LinkUp/AI enrichment |
| created_at | timestamp | |
| ttl_days | int | Default 30 |

### `repair_estimates`
| Column | Type | Notes |
|---|---|---|
| id | UUID | PK |
| listing_id | UUID | FK → listings |
| total_min_pence | int | Sum of all faults |
| total_max_pence | int | |

### `market_values`
| Column | Type | Notes |
|---|---|---|
| id | UUID | PK |
| listing_id | UUID | FK → listings |
| comp_count | int | How many sold comps found |
| median_value_pence | int | |
| source | varchar | "ebay_sold" / "linkup_fallback" |
| confidence | varchar | "high" (≥5 comps) / "medium" (3-4) / "low" (<3) |

### `opportunities`
| Column | Type | Notes |
|---|---|---|
| id | UUID | PK |
| listing_id | UUID | FK → listings |
| listing_price_pence | int | |
| repair_cost_mid_pence | int | midpoint of min/max |
| market_value_pence | int | |
| expected_profit_pence | int | market_value - listing_price - repair_cost_mid |
| score | float | 0.0–1.0 normalised score |
| risk_level | varchar | low/medium/high |
| alerted | bool | Has push notification been sent |
| created_at | timestamp | |

---

## 10. API Endpoints

### `GET /health`
Returns service status. Always implemented first.

### `GET /opportunities`
Query params: `limit` (default 20), `min_profit` (pence), `max_distance_miles`
Returns: Array of opportunity summaries, ranked by score desc.

### `GET /opportunities/{id}`
Returns: Full opportunity detail including faults, repair breakdown, market comps.

### `POST /refresh`
Triggers manual ingestion cycle. Returns job ID.

### `GET /refresh/{job_id}`
Returns: Job status.

---

## 11. eBay API Integration Details

### Auth
- OAuth 2.0 Client Credentials flow
- Scope: `https://api.ebay.com/oauth/api_scope`
- Token cached in memory, refreshed before expiry

### Opportunity Discovery — Browse API
```
GET /buy/browse/v1/item_summary/search
Marketplace: EBAY_GB
Category: 9801 (Cars, Motorcycles & Vehicles > Cars & Trucks)
Keywords: "spares or repair" OR "non runner" OR "spares repair"
Sort: newlyListed
Condition: "FOR_PARTS_OR_NOT_WORKING" (condition ID 7000)
Limit: 50 per poll
```

### Market Value — Browse API (sold comps)
```
GET /buy/browse/v1/item_summary/search
Keywords: "{make} {model} {year}"
Filter: buyingOptions=AUCTION|FIXED_PRICE (completed)
Category: 9801
Marketplace: EBAY_GB
Note: Full sold price data requires Marketplace Insights API approval.
Fallback: Use active listings median as proxy + LinkUp for sold data.
```

### Parts Pricing — Browse API
```
GET /buy/browse/v1/item_summary/search
Keywords: "{part_name} {make} {model} {year}"
Category: 131090 (Vehicle Parts & Accessories)
Marketplace: EBAY_GB
Sort: price (ascending)
Limit: 10
Take: median of bottom 5 results
```

---

## 12. Milestone Order

| # | Milestone | Status |
|---|---|---|
| 1 | Repo scaffold + DB models + event system + healthcheck | ✅ |
| 2 | eBay adapter (stub) + ingestion worker | ✅ |
| 3 | AI problem detection service + fault cache | ✅ |
| 4 | Repair estimation service (static map + cache) | ✅ |
| 5 | Market value service (eBay sold + LinkUp fallback) | 🔲 |
| 6 | Opportunity scoring engine | 🔲 |
| 7 | REST API endpoints | 🔲 |
| 8 | eBay adapter (live) — post API approval | 🔲 |
| 9 | iOS SwiftUI client | 🔲 |
| 10 | Push notifications | 🔲 |

---

## 13. Environment Variables

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@host/flipper

# eBay
EBAY_CLIENT_ID=
EBAY_CLIENT_SECRET=
EBAY_STUB=true          # Set false when live keys approved

# LinkUp
LINKUP_API_KEY=
LINKUP_STUB=true        # Set false when ready

# AI
ANTHROPIC_API_KEY=

# App
ENVIRONMENT=development # development | production
LOG_LEVEL=INFO
POLL_INTERVAL_SECONDS=180
OPPORTUNITY_SCORE_THRESHOLD=0.6
ALERT_DISTANCE_MILES=50
```

---

## 14. Rules Claude Code Must Follow

1. **Never modify existing event types** — only add new ones
2. **Never bypass the adapter interface** — no direct API calls outside adapters/
3. **Never call AI directly** — always via `ai_service.py`
4. **Never call LinkUp directly** — always via `search_service.py`
5. **Always maintain stub compatibility** — stubs must satisfy the same interface
6. **All prices stored in pence** — display conversion happens in the API layer only
7. **Maintain compatibility with existing events and models** on every task

---

*Last updated: Milestone 4 — Repair estimation service with live parts pricing complete*
