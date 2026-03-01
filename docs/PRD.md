# Flipper — Product Requirements Document

**Version:** 2.0
**Status:** Active
**Last updated:** March 2026

---

## 1. Product Overview

### Vision

Flipper is an iOS application that automatically finds UK vehicles listed as "spares or
repair" that represent strong buy-fix-resell opportunities. It does the research a car
flipper would otherwise do manually — finding the car, diagnosing likely faults,
estimating repair costs, benchmarking resale value, and scoring the profit potential —
delivering a simple ranked feed of opportunities with push alerts for the best ones.

### Primary User

Single end-user (personal use). A car flipper who buys damaged/non-running vehicles,
repairs them, and resells at profit. Primarily operating in the UK.

### Design Philosophy

- **High signal, low noise** — only surface genuinely interesting opportunities
- **Extreme simplicity** — minimal buttons, large readable cards, immediate usefulness
- **Fast to act** — from alert to viewing the listing in under 10 seconds

---

## 2. Core User Journey

```
User opens app
  → Sees ranked feed of repair-and-resell opportunities
  → Taps a card
  → Sees: listing summary, detected faults, repair cost estimate, expected profit
  → Taps "View on eBay" → goes to listing
```

Background (no user interaction required):
```
System polls eBay every 3 minutes
  → New spares/repair listing found
  → Faults detected via AI
  → Repair cost estimated
  → Market value benchmarked against eBay sold comps
  → Profit opportunity scored
  → If score exceeds threshold → push notification sent
```

---

## 3. Goals and Non-Goals

### Goals (MVP)

- Detect newly listed spares/repair vehicles on eBay UK
- Identify likely mechanical problems from listing text using AI
- Estimate repair cost ranges per fault
- Estimate resale value using eBay sold comparable listings
- Rank opportunities by expected profit
- Deliver push alerts for high-scoring opportunities within distance radius
- iOS app with feed, detail view, and saved listings

### Non-Goals (MVP)

- Multi-user / accounts
- Dealer tooling or analytics dashboards
- Marketplace posting or negotiation
- Image-based damage detection
- Non-UK markets
- Facebook Marketplace, Gumtree (Phase 3+)

---

## 4. Data Sources

### Phase 1 (MVP) — eBay only

eBay serves as the full-loop data source for MVP. It covers all three data needs:

| Need | eBay Source | Notes |
|---|---|---|
| Opportunity discovery | Browse API — Motors, spares/repair keyword | Sorted by newly listed |
| Market value benchmark | Browse API — completed/sold Motors listings | Marketplace Insights API as upgrade path |
| Parts pricing | Browse API — Parts & Accessories | Filter by vehicle compatibility |

This single-source approach is intentional. It gives us a working end-to-end pipeline
before introducing complexity.

### Phase 2 — Enrichment

- DVLA Vehicle Lookup — confirm make/model/year from registration
- MOT History API — known faults, mileage history, advisories

### Phase 3+ — Additional sources

- AutoTrader (sold comps — richer market value data)
- Gumtree (additional opportunity listings)
- GSF / Euro Car Parts (parts pricing cross-reference)

**Architectural note:** Every data source is behind an adapter interface. Adding a new
source in Phase 3 requires only a new adapter — zero changes to the pipeline.

---

## 5. Web Search (LinkUp)

LinkUp provides AI-powered web search. It is used selectively to control cost.

### Where LinkUp fires

**Fault intelligence (primary use)**
When the AI detects a fault not already in the fault cache:
- Fires one search: `"{make} {model} {fault} common fault repair cost UK"`
- Result stored in fault cache keyed by `(make, model, year_band, fault_type)`
- All future listings with the same fault+model combo use the cache — no further search
- This means cost drops rapidly as the cache fills with common faults on popular models

**Market value fallback (secondary use)**
When eBay returns fewer than 3 sold comps for a vehicle:
- Fires one search: `"{make} {model} {year} sold price UK"`
- Used as supplementary signal, flagged as low-confidence

### Where LinkUp does NOT fire

- Opportunity discovery (eBay handles this)
- Parts pricing primary lookup (eBay handles this)
- Any fault already present in the fault cache
- Any listing that fails the keyword pre-filter (never reaches AI at all)

---

## 6. System Architecture

### Pipeline

```
eBay Motors (spares/repair listings)
          ↓
    Listing Ingestion Worker
    [polls every 3 min, deduplicates, keyword pre-filters]
          ↓ NEW_LISTING_FOUND
    Vehicle Enrichment Worker
    [extracts make/model/year from title/description]
          ↓ VEHICLE_ENRICHED
    AI Problem Detection Service
    [LLM analyses listing text → structured fault list]
    [LinkUp fires here if fault not in cache]
          ↓ PROBLEMS_DETECTED
    Repair Estimation Service
    [maps faults → cost ranges using cache + static knowledge base]
          ↓ REPAIR_ESTIMATED
    Market Value Service
    [eBay sold comps → median value]
    [LinkUp fallback if < 3 comps]
          ↓ MARKET_VALUE_ESTIMATED
    Opportunity Scoring Engine
    [profit = market_value - listing_price - repair_cost_mid]
    [score = normalised 0.0–1.0]
          ↓ OPPORTUNITY_CREATED
    Backend API → iOS App
```

### Key architectural rules

- **One backend service** — no microservices
- **Event-driven pipeline** — each step emits an event, next step subscribes
- **Adapter pattern** — all external sources behind abstract interfaces
- **AI is gated** — listings only reach the LLM after passing keyword pre-filter
- **Cache-first** — fault intelligence cached by model+fault type, never re-fetched
- **Stubs always available** — every adapter has a stub mode for development/testing

---

## 7. AI Cost Controls

LLM calls are the primary cost vector. The following controls are mandatory:

### 1. Keyword pre-filter
A listing only enters the AI pipeline if its title or description contains at least
one of:
```
spares, repair, non-runner, fault, issue, damage, blown, seized,
knocking, smoking, misfire, gearbox, clutch, timing, needs work
```
Listings that don't match are stored but not processed.

### 2. Fault cache
Every AI-generated fault diagnosis is cached by `(make, model, year_band, fault_type)`.
Cache TTL: 30 days. On a cache hit, no LLM call is made.

### 3. Model selection
- `claude-haiku` for fault classification (fast, cheap)
- `claude-sonnet` only for complex multi-fault analysis where haiku confidence is low

### 4. Token limits
- Fault detection: max 512 output tokens
- Repair estimate: max 256 output tokens

---

## 8. Opportunity Scoring

### Profit calculation
```
expected_profit = market_value - listing_price - repair_cost_midpoint
```

Where:
- `repair_cost_midpoint = (repair_min + repair_max) / 2`
- `market_value` = median of eBay sold comps (or LinkUp fallback)

### Score (0.0 – 1.0)
Normalised across active opportunities. Factors:
- Expected profit (primary weight: 60%)
- Market value confidence — number of sold comps (20%)
- Fault severity and drivability (10%)
- Listing age — newer is better (10%)

### Risk level
| Level | Criteria |
|---|---|
| Low | ≥5 sold comps, single known fault, driveable |
| Medium | 3-4 comps, or multiple faults |
| High | <3 comps, non-runner, or unknown fault type |

### Alert threshold
Push notification fires when:
- `score >= 0.6` (configurable via env var)
- `distance <= 50 miles` from user location (configurable)
- Not previously alerted

---

## 9. Database Schema

### `listings`
| Column | Type | Notes |
|---|---|---|
| id | UUID | PK |
| source | varchar | "ebay" |
| external_id | varchar | eBay item ID — unique per source |
| title | text | |
| description | text | |
| price_pence | int | All prices stored in pence |
| postcode | varchar | |
| url | text | Direct link to listing |
| raw_json | jsonb | Full API response |
| processed | bool | Has entered the pipeline |
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
| severity | varchar | low / medium / high |
| source | varchar | "ai" or "keyword" |

### `fault_cache`
| Column | Type | Notes |
|---|---|---|
| id | UUID | PK |
| cache_key | varchar | UNIQUE: `{make}_{model}_{year_band}_{fault}` |
| repair_min_pence | int | |
| repair_max_pence | int | |
| repair_notes | text | Source intelligence summary |
| created_at | timestamp | |
| ttl_days | int | Default 30 |

### `repair_estimates`
| Column | Type | Notes |
|---|---|---|
| id | UUID | PK |
| listing_id | UUID | FK → listings |
| total_min_pence | int | |
| total_max_pence | int | |

### `market_values`
| Column | Type | Notes |
|---|---|---|
| id | UUID | PK |
| listing_id | UUID | FK → listings |
| comp_count | int | Number of sold comps found |
| median_value_pence | int | |
| source | varchar | "ebay_sold" / "linkup_fallback" |
| confidence | varchar | "high" (≥5) / "medium" (3-4) / "low" (<3) |

### `opportunities`
| Column | Type | Notes |
|---|---|---|
| id | UUID | PK |
| listing_id | UUID | FK → listings |
| listing_price_pence | int | |
| repair_cost_mid_pence | int | |
| market_value_pence | int | |
| expected_profit_pence | int | |
| score | float | 0.0–1.0 |
| risk_level | varchar | low / medium / high |
| alerted | bool | Push notification sent |
| created_at | timestamp | |

---

## 10. Backend API

### `GET /health`
Service status and DB connectivity check.

### `GET /opportunities`
Returns ranked opportunity feed.
Query params: `limit` (default 20), `min_profit_pence`, `max_distance_miles`
Sorted by: `score` descending

### `GET /opportunities/{id}`
Full opportunity detail:
- Listing summary
- Detected faults with severity
- Repair cost breakdown per fault
- Market value with comp count and confidence
- Expected profit
- Risk level
- Link to eBay listing

### `POST /refresh`
Triggers a manual ingestion cycle immediately.
Returns: `{"job_id": "..."}`

### `GET /refresh/{job_id}`
Returns job status: `pending / running / complete / failed`

---

## 11. iOS App

### Design principles
- Minimal cognitive load — user should understand a card in 3 seconds
- Large readable text — used while looking at cars in person
- One primary action per screen
- Dark mode support

### Screens

**Home — Opportunity Feed**
- Scrollable list of opportunity cards
- Each card: car name, price, expected profit, risk badge, distance
- Pull to refresh
- Saved / All toggle

**Detail View**
- Car title and listing price
- Detected faults (list with severity indicators)
- Repair cost range (min–max, per fault breakdown on expand)
- Market value (with comp count shown for transparency)
- Expected profit (prominent)
- Risk level badge
- "View on eBay" button (opens Safari)
- Save / unsave

**Notifications**
- Push notification on high-score opportunity
- Format: `🔥 BMW 320d — £750 | Est. profit +£1,400 | 10 miles`

---

## 12. Development Phases

### Phase 1 — Working MVP
- eBay listing ingestion (stub → live)
- AI fault detection with keyword pre-filter
- Repair estimation (fault cache + static knowledge base)
- Market value via eBay sold comps
- Opportunity scoring
- REST API
- Basic iOS feed and detail view

### Phase 2 — Enrichment
- DVLA registration lookup
- MOT history integration
- Improved fault detection using MOT advisory history

### Phase 3 — Intelligence
- Parts pricing via eBay Parts API
- Image-based damage signals
- Richer repair cost database

### Phase 4 — Expansion
- Additional listing sources (Gumtree, AutoTrader)
- Sold comp data from AutoTrader
- Negotiation assistance features

---

## 13. Success Metrics

- Relevant alert rate (opportunities that user saves or acts on)
- Time from listing posted → alert delivered (target: < 5 minutes)
- Expected vs actual profit accuracy (tracked over time)
- Opportunities saved per week

---

## 14. Technical Constraints

- Backend: Python, FastAPI, PostgreSQL, SQLAlchemy async
- Hosting: Railway
- AI: Anthropic Claude API
- Web search: LinkUp API
- Mobile: iOS SwiftUI
- All prices stored and computed in pence (GBP)
- UK market only (EBAY_GB marketplace)
- eBay API: Browse API v1 (application OAuth token)
