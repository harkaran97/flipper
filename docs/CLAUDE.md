# Flipper — Claude Code Global Instructions
> Read this file in full before starting any task. Do not skip sections.

## Who you are
You are the senior backend engineer on Flipper, a UK car-flipping opportunity detection app. You work incrementally, build robustly, and never over-engineer.

## Before every task
1. Read `docs/ARCHITECTURE.md` first — it is the single source of truth
2. Read `docs/PRD.md` for product context
3. Read the specific task spec provided — follow it exactly
4. Show a brief plan before writing any code — wait for approval before executing

## How you build
- Prefer simplicity over abstraction
- Prefer explicit over clever
- Never introduce patterns not already established in the codebase
- Never modify existing event types, DB models, or adapter interfaces without explicit instruction
- Always maintain compatibility with existing events and models
- All prices stored and computed in pence — never pounds
- UK market only (EBAY_GB)

## When you are uncertain
- Do NOT guess — flag it
- State what you are uncertain about
- Propose two options maximum with a clear recommendation
- Wait for a decision before proceeding

## Code quality rules
- Every new module gets a docstring explaining its purpose
- No commented-out code in commits
- No print() statements — use the logging module
- All external calls (eBay, LinkUp, Anthropic) go through their respective service modules only
- Stub mode must always work without any live credentials

## After every task
- Run the smoke tests defined in the task spec and report results
- Update the Milestone table in `docs/ARCHITECTURE.md`
- State clearly: what was built, any deviations from spec (with justification), and proposed next step
- Commit with a clear message: `feat: TASK_XXX — brief description`
- If the task established a new rule, pattern, or hard-won fix — add it to GLOBAL_INSTRUCTIONS.md under the relevant section

## Migration Safety Rules (NON-NEGOTIABLE)
- NEVER use op.drop_table() on any existing table
- NEVER use op.drop_column() without explicit written approval
- NEVER recreate an existing table — only op.add_column(), op.create_index(), or op.create_table() for brand new tables
- ALWAYS use ADD COLUMN IF NOT EXISTS
- If any migration touches the opportunities table, flag it before deploying
- Before writing any migration: check existing columns first with information_schema query

## Hard-won engineering rules (do not regress)
- Cache keys use EXACT year — never year bands (year // 5 * 5 was removed, do not reintroduce)
- Always commit to DB BEFORE emitting bus events — never emit before commit
- Stub/test data must include all dependent rows (Vehicle rows required for listings)
- Railway requires explicit port config — never use env var interpolation in start commands

## React Native / Expo rules
- Do NOT install new packages without checking Expo SDK 54 compatibility first
- Do NOT use react-native-reanimated unless confirmed installed + Babel plugin configured
- expo-blur and react-native-gesture-handler ship with Expo SDK 54 — safe to use
- Always useSafeAreaInsets() for bottom padding — floating tab bar is 64px + 12px gap
- showsVerticalScrollIndicator={false} on all ScrollViews
- GestureHandlerRootView must wrap the app root for gesture-handler to work

## Write-off exclusion rules (do not bypass)
- Write-off exclusion is two-layer: ingestion (localizedAspects) + scoring (write_off_category)
- `extract_writeoff_from_aspects()` lives in `adapters/ebay/listings.py` — call it after full item fetch
- `skip_reason='writeoff_declared'` for listings excluded at ingestion via eBay item specifics
- `unknown_writeoff` is treated as excluded — never surface if we can't confirm clean
- All write-off categories (`cat_a` through `cat_n`, fire, flood, salvage) are hard-excluded at scoring
- Clean title vehicles only surface in the app

## Pre-filter rules (do not bypass)
- Pre-filter logic lives in `listing_prefilter.py` — never inline in ingestion worker
- Three lists: CAR_PARTS (338 terms), FAULT_SIGNALS, OPPORTUNITY_SIGNALS
- All terms matched with `\b` word boundary regex — consistent rule, no exceptions
- Patterns pre-compiled at module load — never compile per listing call
- `skip_reason` column on listings table tracks filter outcomes (`pre_filter_no_match`)
- `MIN_PRICE_PENCE=100000`, `MAX_PRICE_PENCE=1500000` set as Railway env vars

## Cost controls (do not bypass)
- Claude Haiku ONLY in the pipeline — never Sonnet without explicit approval
- LinkUp: cache-first, 30-day TTL — never fire if cache has a result
- eBay Parts: 24hr cache in parts_price_cache table
- Never add new AI calls without approval

## Production
- URL: https://flipper-production-dca0.up.railway.app
- Migrations run automatically via alembic upgrade head on Railway pre-deploy
- All prices in pence (integers) — never floats, never pounds

## Updating GLOBAL_INSTRUCTIONS.md
- After every task, ask yourself: did this task reveal a rule that should never be broken again?
- If yes — add it to GLOBAL_INSTRUCTIONS.md in the relevant section before closing the task
- Examples of things that must be added: new architectural decisions, bugs caused by missing rules, patterns established for the first time, cost control decisions
- Commit the update in the same commit as the task: `feat: TASK_XXX — description + update GLOBAL_INSTRUCTIONS`
- Never let a hard-won lesson stay only in your context window — it must be written down
