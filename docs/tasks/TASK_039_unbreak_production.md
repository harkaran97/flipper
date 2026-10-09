# TASK 039 — Unbreak production: missing column, dead scheduler, stale feed

**Reference:** `docs/ARCHITECTURE.md`, `docs/CLAUDE.md`
**Milestone:** 39
**Depends on:** TASK_038

---

## Context

Production silently broken since 31 March 2026 (verified 9 Oct 2026 against `main` @ `3f564d7`):

- `/health` → `last_poll: 2026-03-31T09:10:45Z`; nothing polled since.
- Newest opportunity `created_at` is 2026-03-30.
- `GET /api/v1/opportunities/{id}` 500s for every opportunity.

### Root cause 1 — `market_values.sold_comp_urls` missing in prod
Migration 014 never created the column. Detail endpoint selects it → `UndefinedColumn`.
Valuation insert fails → no `MarketValue` row → `load_opportunity_inputs` raises → no opportunities.
Migration 014 also broke the "ADD COLUMN IF NOT EXISTS" rule.

### Root cause 2 — scheduler crash at month end
`_next_9am_utc()` used `.replace(day=day + 1)` → `ValueError` on the last day of a month.
The call sat outside the `try`, so the `asyncio` task died silently.

### Root cause 3 — stale feed
136 March opportunities still served; the eBay ads are long gone.

## Implementation

1. **DB (manual, Railway Postgres console, before deploy)**
   ```sql
   -- 1a (expect 0 rows)
   SELECT column_name FROM information_schema.columns
   WHERE table_name = 'market_values' AND column_name = 'sold_comp_urls';
   -- 1b
   SELECT version_num FROM alembic_version;
   -- 1c
   ALTER TABLE market_values ADD COLUMN IF NOT EXISTS sold_comp_urls JSON;
   -- 1d
   UPDATE alembic_version SET version_num = '014';
   ```
   Report 1a/1b before running 1c/1d. If 1a returns a row, stop.
2. **Migration 014** — `upgrade()` becomes `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`.
3. **Ingestion worker** — `_next_9am_utc` uses `timedelta(days=1)`; whole loop body in
   `try/except Exception` with `exc_info=True` and a 1-hour back-off; `run_once` returns
   `stats["passed"]`.
4. **Feed** — `get_opportunities` hides opportunities older than 14 days. Not applied to
   saved/builds.
5. **/health** — `pipeline.ingestion` is `"stale"` if `last_poll_time` is `None` or > 26h old,
   else `"ok"`. Unmeasured entries removed.

## Smoke tests

1. SQL 1a returns 1 row after step 1.
2. `tests/unit/test_ingestion_scheduler.py`: 31 Mar, 31 Dec and 29 Feb 2028 roll over correctly.
3. After deploy: `/health` → `ingestion: "stale"`; detail endpoint → 200 with `sold_comp_urls`;
   feed `total` → 0.
4. `POST /api/v1/trigger-poll` → 202; logs show `[PRE-FILTER SUMMARY]` and
   `Opportunity scored for listing`; new `market_values` rows have non-empty `sold_comp_urls`.
5. Next morning: `/health` → `last_poll` ~09:0x UTC, `ingestion: "ok"`.
6. App: detail screen loads.
