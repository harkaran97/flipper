# TASK 040 — Correct and complete data

**Reference:** `docs/ARCHITECTURE.md`, `docs/CLAUDE.md`
**Milestone:** 40
**Depends on:** TASK_036 (pre-filter), TASK_037 (write-off filter), TASK_038 (sold comp URLs), TASK_039
**Engineer:** Claude Code

---

## Objective

Every card in the feed must describe a real, whole car, with numbers that add up and the
fields the redesign (TASK_042, see the Flipper redesign mockup) needs. No app changes in
this task: backend only.

Two outcomes:

1. **Bad rows never reach the feed.** Parts listings, cars with an unknown year, and
   listings with no detected fault are stopped before they cost valuation spend or get
   scored.
2. **The API sends what the cards show.** Vehicle name, photo, mileage, town, listing
   time, fault names, and a fix cost that makes `sell − buy − fix = profit` exact.

---

## Why (verified against `main` @ `c0f05f3` and prod data)

Production row `8ba365ca-…` — title "vw golf r mk7.5 wing" — is a body panel scored
`strong` at 97.7% margin with `year: 0`, no faults, £0 parts, market value £6,499. Four
separate gaps let it through:

| # | Gap | Where |
|---|---|---|
| G1 | Tier 1 of the pre-filter passes any listing that **mentions a car part**. A parts listing mentions a part by definition, so every one passes. | `listing_prefilter.py` `CAR_PARTS` |
| G2 | The AI prompt says "infer any missing vehicle fields", but the JSON output schema has **no field to return them in**. Only `trim` is written back. Year stays 0 for every listing whose year is not in eBay specifics or the title. | `ai_service.py` prompt + schema, `problem_detector.py` step 5d |
| G3 | Valuation runs with `year = 0`, so the sold-comps query drops the year and matches every Golf R of any age ("high confidence, 21 comps"). | `market_valuator.py` `build_vehicle_query` |
| G4 | `classify_opportunity` has no guard for zero faults, `year == 0`, or an implausible value-to-price ratio, so £0 repairs on a £150 listing score as `strong`. | `opportunity_scorer.py` |

Smaller correctness bugs found on the way:

- **G5** — Detail endpoint per-fault parts range uses `min(cheapest per part)` and `max(cheapest per part)` instead of sums. A fault needing three parts shows "£45–£980" instead of "£1,250". Display only; `true_profit` uses `RepairEstimate` and is unaffected. (`opportunities.py` ~L335)
- **G6** — Title year fallback regex is capped at 2025 (`20(?:0[0-9]|1[0-9]|2[0-5])`). Pre-2000 cars and 2026+ plates are never matched. (`listings.py` `_parse_from_title`)
- **G7** — The AI returns `evidence` (the seller's exact phrase) per fault and it is discarded. Fault `description` shown in the app is the generic `CommonProblem.description`, not what is wrong with *this* car.
- **G8** — The card API sends no photo, mileage, town, listing time or fault names, and no fix cost. The app currently re-derives numbers and expects a `detected_faults_summary` field that does not exist (every card shows "—").
- **G9** — `MIN_PRICE_PENCE` is £1,000 (see CLAUDE.md), yet the wing came in at £150. The Browse API search sends `price:[min..max]` without `priceCurrency:GBP`. eBay's docs say the price filter must be paired with `priceCurrency`; without it the filter is not applied as intended. There is also no in-code price check after the fetch. (`listings.py` `search_listings`, `ingestion_worker.py`)

---

## Context to load

- `backend/app/services/listing_prefilter.py`
- `backend/app/workers/ingestion_worker.py`
- `backend/app/adapters/ebay/listings.py`
- `backend/app/adapters/ebay/stub.py`
- `backend/app/services/ai_service.py` (prompt, output schema, `STUB_AI_RESPONSE`)
- `backend/app/services/problem_detector.py`
- `backend/app/services/opportunity_scorer.py`
- `backend/app/models/listing.py`, `vehicle.py`, `fault.py`
- `backend/app/api/schemas.py`, `backend/app/api/opportunities.py`

---

## Changes

### 1. Stop parts listings (G1, G9) — cheapest layer first

**1-0. Price band actually enforced (G9).** In `search_listings`, add `priceCurrency:GBP` to
the `filter` string next to `price:[…]`. In `run_poll_cycle`, before storing, skip any
listing whose `price_pence` is outside `min_price_pence..max_price_pence`. Count these as
`out_of_price_band` in the poll stats, and don't store them, because they were never meant
to be fetched.

**1a. Ingestion, no AI cost.** In `run_poll_cycle`, after the full item fetch and before the
pre-filter: if the full item's `localizedAspects` contain **neither** a year
(`year`, `registration year`) **nor** a mileage (`mileage`, `vehicle mileage`) aspect, store
with `skip_reason='not_whole_vehicle'`, `processed=True`, commit, continue. Whole cars in
category 9801 carry these; a miscategorised wing does not. Only apply when the full item
fetch succeeded — never on summary data alone.

**1b. AI classification.** Add to the AI output schema:

```json
"listing_type": "whole_vehicle|parts_only|unclear"
```

with a prompt line: *"parts_only = the listing sells a component or panel, not a complete car."*
In `problem_detector.py`, if `listing_type == "parts_only"`: set
`listing.skip_reason='not_whole_vehicle_ai'`, commit, and **do not emit**
`PROBLEMS_DETECTED`. `unclear` continues as today.

**1c. Scorer guard.** See step 4.

### 2. Infer and persist missing vehicle fields (G2, G6)

**2a. AI output schema.** Add:

```json
"vehicle": {
  "make": "<string or null>", "model": "<string or null>", "year": <int or null>,
  "mileage": <int or null>, "fuel_type": "<string or null>",
  "transmission": "<string or null>", "body_type": "<string or null>"
}
```

Prompt: *"Fill ONLY the fields listed under FIELDS REQUIRING AI INFERENCE. Use null when the
listing does not say. Never guess."*

**2b. Write-back.** In `problem_detector.py` next to the existing trim write-back (step 5d),
write each returned field onto the `Vehicle` row **only if the current value is missing**
(`None`, `"Unknown"` or `0`). Validate: year in `1980..current_year + 1`, mileage in
`1..500000`. Log each field set, e.g. `[DETECTOR] Step 5d: Vehicle year set to 2015 from AI`.

**2c. Stop unknown years before valuation.** After write-back, if `vehicle.year` is still
0: set `listing.skip_reason='year_unknown'`, commit, do not emit. This saves the eBay sold
search and LinkUp call for listings we cannot value.

**2d. Title regex.** In `_parse_from_title`, match `19[8-9]\d|20\d{2}` and reject values
above `current_year + 1`.

Commit before emit stays as is. The valuation worker already reads the `Vehicle` row
after detection commits, so it sees the inferred year.

### 3. Keep the seller's words per fault (G7)

**3a. AI output.** Per fault, add
`"explanation": "<one plain-English sentence a non-mechanic understands, max 20 words>"`.
Keep `evidence` as is.

**3b. Model + migration.** Add to `DetectedFault`:

```python
evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
```

Migration `015_listing_display_fields.py` (shared with step 5) — idempotent per CLAUDE.md:

```python
op.execute("ALTER TABLE detected_faults ADD COLUMN IF NOT EXISTS evidence TEXT")
op.execute("ALTER TABLE detected_faults ADD COLUMN IF NOT EXISTS explanation TEXT")
```

Store both when creating `DetectedFault` rows.

### 4. Scorer guards (G4)

In `classify_opportunity`, add hard excludes after the write-off check. Each logs its reason
at INFO with the listing id:

| Rule | Reason logged |
|---|---|
| `year == 0` | `year_unknown` |
| zero detected faults, and margin under 40% or low confidence | `no_faults_detected`. See Decisions 2: otherwise capped at `SPECULATIVE`. |
| `market_value_pence > 10 × listing_price_pence` | `price_implausible`. Likely a part, a typo or a scam. The ratio is configurable as `MAX_VALUE_TO_PRICE_RATIO`, default 10. |

`classify_opportunity` gains keyword-only `year: int` and `fault_count: int` parameters;
pass them from `score_opportunity`. Do not change the `Opportunity` model.

### 5. Display fields stored at ingestion (G8)

Add to `Listing` (same migration 015, `ADD COLUMN IF NOT EXISTS`):

| Column | Type | Source (full item first, then summary `raw_json`) |
|---|---|---|
| `image_urls` | `JSON` | `image.imageUrl` + `additionalImages[].imageUrl`, upscaled (below), max 12 |
| `location_town` | `String(100)` | `itemLocation.city`, else outward code of `itemLocation.postalCode` |
| `listed_at` | `DateTime(timezone=True)` | `itemCreationDate` |
| `distance_miles` | `Float` | `location_service` from `itemLocation.postalCode` (Decisions 1) |

**Upscale helper** in `listings.py`:

```python
def upscale_ebay_image(url: str) -> str:
    """eBay serves s-l225 thumbnails in search results; request s-l1600."""
    return re.sub(r"/s-l\d+\.", "/s-l1600.", url)
```

**Existing rows.** No backfill script. At read time, fall back to
`raw_json["image"]["imageUrl"]` (summary data already stored), `raw_json["itemLocation"]`
and `listing.created_at`.

**Verify first.** Before writing the extraction, log one real `getItem` response's
`itemLocation`, `image`, `additionalImages` and `itemCreationDate` keys from a live poll.
Confirm the field names against it; do not code from memory.

### 6. API fields (G5, G8)

**`OpportunityCard`** (and therefore `OpportunityDetail`) gains:

```python
vehicle_name: str            # "2015 Volkswagen Golf R" — year + make + model (+ trim)
image_url: str | None        # first of image_urls, upscaled
mileage: int | None
location: str | None         # "Leicester" or "LE4"
listed_at: str | None        # ISO8601
fault_names: list[str]       # max 3, highest severity first, display-formatted
fix_cost_pence: int          # parts_cost_mid + effort_cost — the exact figures true_profit used
```

`vehicle_name` keeps the model's casing from eBay specifics. It title-cases the model only
when it is entirely lower case (so "golf" becomes "Golf", while "320d" and "CX-5" are left
as they are), and omits the year when it is 0.

`fix_cost_pence` must make `market_value_pence − listing_price_pence − fix_cost_pence ==
true_profit_pence` exactly. Compute it with the same `calculate_true_profit` call, never in
the app.

**`OpportunityDetail`** additionally gains `image_urls: list[str]`. `FaultDetail` gains
`explanation: str | None` and `seller_quote: str | None` (from `evidence`). `description`
falls back to `CommonProblem.description` as today.

**G5 fix:** per fault, `fault_parts_total_min_pence = sum(cheapest supplier per part)` and
`fault_parts_total_max_pence = sum(most expensive supplier per part)`.

Build the card fields once in `_format_card` and reuse it in feed, saved and builds.

### 7. Stub data

Stubs must exercise every new path (CLAUDE.md: stub mode always works):

- `EbayStubAdapter.search_listings` — every listing gets `image`, `itemLocation.city`,
  `itemCreationDate` in `raw_json`, plus **one parts-only listing** ("vw golf r mk7.5 wing",
  £150, no year or mileage aspects) that must be skipped.
- `STUB_AI_RESPONSE` — add `listing_type`, `vehicle`, and per-fault `explanation`.

---

## Rule checks (CLAUDE.md)

- **No new AI calls.** Steps 1b, 2a and 3a add fields to the existing Haiku detection call.
- **Models touched:** `Listing` and `DetectedFault` (new nullable columns) and `Vehicle`
  (values only). **`opportunities` table not touched.** This spec is the explicit
  instruction CLAUDE.md requires for model changes.
- **Write-off rules unchanged:** clean-title vehicles only, as today.
- **Pre-filter lists unchanged.** The whole-vehicle check is a helper,
  `has_vehicle_aspects(localized_aspects)`, in `adapters/ebay/listings.py` next to
  `extract_writeoff_from_aspects()`. The ingestion worker calls it in the same place as the
  write-off check. It is not keyword logic, so it does not belong in `listing_prefilter.py`.

---

## Out of scope

- Number plate capture, history checks (stolen, write-off, finance, mileage): **v2**.
- Any mobile app change: TASK_041 (behaviour) and TASK_042 (redesign).
- Rescoring the 136 March rows. The 14-day feed window from TASK_039 hides them.

---

## Decisions (9 Oct 2026)

1. **Distance: yes, via postcodes.io.** eBay gives only an outward code such as "LE4".
   - A new module, `app/services/location_service.py`, looks up the outward code's
     latitude/longitude on postcodes.io (free, no key) and works out the haversine distance
     in miles from `USER_POSTCODE`.
   - Lookups are cached in memory. The result is stored on `listings.distance_miles` at
     ingestion, so each listing is looked up once.
   - It uses built-in coordinates whenever `EBAY_STUB=true`: no network in stub mode, and no
     new env var.
   - Any failure returns `None` and never blocks ingestion.
2. **Zero-fault listings: "Worth checking" only when the profit is strong.** With no fault
   detected, `classify_opportunity` returns `SPECULATIVE` (shown as "Worth checking" in
   TASK_042) only if margin is at least 40% and market value confidence is high or medium,
   the same bar as `STRONG`. Otherwise `EXCLUDE`. Such a card is never `STRONG`. The API sends
   `profit_is_best_case: true` so the app can say the profit assumes nothing else is wrong.
   This replaces the "zero detected faults" exclude row in step 4.

---

## Acceptance Criteria

### 1. Unit — parts listing stopped at ingestion
`tests/unit/test_whole_vehicle_filter.py`:
- An item with no year or mileage aspects is skipped with `not_whole_vehicle`. An item with
  either one passes.
- A £150 listing is dropped as `out_of_price_band` when `MIN_PRICE_PENCE=100000`.
- The `filter` string built by `search_listings` contains `priceCurrency:GBP`.

### 2. Unit — scorer guards
`tests/unit/test_classify_guards.py`: each of `year=0`, `fault_count=0` and a value/price
ratio of 11 returns `EXCLUDE`. A normal case still returns `STRONG`.

### 3. Unit — fix cost arithmetic
For a set of fixtures, `market_value − listing_price − fix_cost == true_profit`.

### 4. Unit — helpers
`upscale_ebay_image("https://i.ebayimg.com/images/g/abc/s-l225.jpg")` ends in `/s-l1600.jpg`.
The title year fallback finds 1998 and 2026 and rejects 2031.

### 5. Unit — parts range sums (G5)
A fault with parts priced 980/215/55 (cheapest each) gives `total_min == 1250`.

### 6. Stub end-to-end
With `EBAY_STUB=true` and no API keys: run one poll cycle, then `GET /api/v1/opportunities`.
- The wing listing has `skip_reason='not_whole_vehicle'` and no opportunity.
- Every card has non-empty `vehicle_name`, `image_url`, `location`, `fault_names` and a
  `fix_cost_pence` that satisfies criterion 3.
- No card has `year == 0`.

### 7. Migration
`alembic upgrade head` runs twice in a row without error. Columns exist per
`information_schema.columns`.

### 8. After deploy (prod)
- `POST /api/v1/trigger-poll` → 202. After about 10 minutes:
  ```sql
  SELECT skip_reason, count(*) FROM listings
  WHERE created_at > now() - interval '1 hour' GROUP BY 1;
  ```
  shows the new reasons where they apply.
- `GET /api/v1/opportunities`: no card with `year == 0` or empty `fault_names`. At least 90%
  of cards have `image_url`.

### 9. All existing tests pass
`tests/unit/test_ingestion_scheduler.py` and `tests/smoke/test_parts_pricing.py`.

---

## After Completion

- Update the milestone table in `docs/ARCHITECTURE.md`.
- Add to "Hard-won engineering rules" in `docs/CLAUDE.md`:
  - "A prompt that asks the AI to infer a field must have a schema slot for it and a
    write-back, or the inference is lost."
  - "The app never re-derives money figures: the API sends every number the UI shows."
- Commit: `feat: TASK_040 — correct and complete data`.
- Report: files changed, smoke test results, any deviations from this spec.

---

*Task authored by: Flipper CTO/CPO*
*Depends on: TASK_036, TASK_037, TASK_038, TASK_039*
