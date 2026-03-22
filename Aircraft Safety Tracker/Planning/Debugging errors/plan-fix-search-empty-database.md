# Plan: Fix Search Autocomplete Returning “No aircraft found”

## Summary
The UI search flow is working, but the database currently contains **0 Aircraft rows**, so every query returns no results. This plan makes the app resilient by ensuring development environments have data and by improving the empty-database UX.

## What’s Broken (Observed)
- Searching `boeing` returns “No aircraft found matching …” (screenshot).
- Backend search endpoint uses case-insensitive DB filtering and should work when data exists: `Aircraft.model_name.ilike(...)`.
- Runtime check confirms the database is empty: `Aircraft.query.count() == 0`.

## Root Cause
**No aircraft records are loaded** in the current environment. This is a data-loading/bootstrap issue, not a search algorithm issue.

## Options (Simplest First)
1. **Seed local DB on startup/dev setup (Recommended)**
   - Automatically populate a small, deterministic dataset when the DB is empty (dev-only).
   - Pros: Fastest way to make the app usable locally; minimal moving parts.
   - Cons: Must ensure it never runs in prod by accident; must be idempotent.

2. **Empty-database UX guard + “Load data” call-to-action**
   - Keep search behavior, but detect empty DB and show a clearer message (e.g., “No data loaded yet”).
   - Pros: Improves clarity; no automatic writes.
   - Cons: Still requires a separate step to load data.

3. **Hybrid (seed + UX guard)**
   - Seed in dev + show explicit empty-db messaging when empty.
   - Pros: Best UX/DevEx.
   - Cons: Slightly larger diff than Option 1.

## Recommended Approach
**Do Option 3 (Hybrid)**:
- Seed in dev environments (small synthetic dataset) when DB is empty.
- Also distinguish “empty DB” vs “no match” in the search results UI.

This keeps code explicit and robust while minimizing scope.

## Execution Phases

### Phase 1: Data Availability Guard (Dev-only)
- Add a dev-only bootstrap that checks `Aircraft.count()`.
- If zero, insert a small synthetic set of Aircraft rows.
- Make seeding idempotent (e.g., upsert by model_name/manufacturer or check before insert).
- Gate behind an environment variable (example: `ENABLE_DEV_SEED=true`) and/or Flask environment check.

### Phase 2: UX Hardening for Empty DB
- Update `/search` behavior:
  - If DB empty, return a component state that says “No data loaded yet” and suggests next action.
  - If DB has data but no match, keep “No aircraft found matching …”.
- Update the search results component to render the empty-db message distinctly.

### Phase 3: Tests
- Add/extend route tests to cover:
  - Empty DB returns “No data loaded yet”.
  - Seeded DB returns results for `boeing`.
  - “No match” message still works when DB has data.

### Phase 4: Operational Safety + Observability
- Avoid logging sensitive data (no query logging beyond minimal context).
- Log a single info line when seeding runs (count inserted).
- Fail loudly on seed/import errors in dev so the issue is obvious.

## Verification Checklist
- Manual:
  - Load home page, type `boeing`, see results list.
  - Click a result, confirm aircraft page loads.
- Automated:
  - Run existing pytest suite and confirm green.
  - Add targeted tests for empty-db and seeded-db flows.

## Rollback Plan
- Disable dev seed via env var (or by removing dev-only hook) to revert behavior.
- Reverting UX change is safe and isolated to the search result component and/or `/search`.

## Risks
- Dev seeding accidentally enabled in prod/staging.
- Duplicate rows if seeding is not idempotent.
- Startup slowdown if seed grows too large (keep dataset small).

## Open Questions (Need Product/Owner Choice)
1. Environment target for auto-seed:
   - A) Local dev only (recommended)
   - B) Dev + staging
   - C) All environments
2. Seed source:
   - A) Synthetic fixture (recommended)
   - B) Existing scraper output
   - C) Live scrape at startup
3. Empty DB UX:
   - A) Explicit “data not loaded” message (recommended)
   - B) Keep current messaging
   - C) Redirect to a setup/load-data page

