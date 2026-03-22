## Relevant Files

- `Planning/Debugging errors/plan-fix-search-empty-database.md` - Source plan describing the intended fix and tradeoffs.
- `app/routes.py` - `/search` endpoint and search result rendering logic.
- `app/templates/index.html` - HTMX search input that drives autocomplete.
- `app/templates/components/search_results.html` - UI for “no results” vs “empty DB” messaging.
- `app/__init__.py` - App factory; good place for dev-only bootstrap hooks (guarded).
- `run.py` - Local entrypoint; alternative place for dev-only seed triggering (guarded).
- `scripts/import_data.py` - Existing importer that can populate Aircraft/Incident from `data/raw/*.json`.
- `data/raw/boeing_incidents.json` - Local dataset used by importer.
- `data/raw/airbus_incidents.json` - Local dataset used by importer.
- `tests/test_routes.py` - Add coverage for empty-db vs no-match search behavior.
- `tests/conftest.py` - Test DB setup; useful for creating an “empty DB” test case.

### Notes

- Use `PYTHONPATH=. pytest -v` to run the backend test suite.
- Keep any auto-seeding strictly dev-only and gated behind an environment flag to avoid surprises in prod/staging.

## Tasks

- [x] 1.0 Confirm and document the empty-database failure mode
  - [x] 1.1 Verify search route failure state when DB is empty.
  - [x] 1.2 Identify optimal injection point for dev-only seeding (e.g., `run.py` or app context).
- [x] 2.0 Add dev-only data bootstrap for empty databases (gated + idempotent)
  - [x] 2.1 Add an environment check (e.g., `FLASK_ENV=development` or `AUTO_SEED=true`) to guard seed execution.
  - [x] 2.2 Create a lightweight wrapper around `scripts/import_data.py` to seed a small subset if `Aircraft.query.count() == 0`.
  - [x] 2.3 Wire the auto-seed logic into the local startup flow (`run.py` before `app.run()`).
- [ ] 3.0 Improve search UX to distinguish “empty DB” vs “no match”
  - [ ] 3.1 Update `app/routes.py` `/search` endpoint to explicitly check for `Aircraft.query.count() == 0`.
  - [ ] 3.2 If DB is empty, render a specific empty-state template/message instead of the generic "no results".
  - [ ] 3.3 Update `app/templates/components/search_results.html` to handle the empty DB state distinctly from a "no match" state.
- [ ] 4.0 Add automated tests for empty-db search and seeded search results
  - [ ] 4.1 Add test in `tests/test_routes.py` asserting the empty DB message is returned when no aircraft exist.
  - [ ] 4.2 Ensure existing tests pass and correctly handle seeded DBs.
- [ ] 5.0 Add verification + rollback notes to prevent regressions and prod risk
  - [ ] 5.1 Document the `AUTO_SEED` env var requirement in `README.md` or a dev setup guide.
  - [ ] 5.2 Confirm rollback path (just unset the env var) is documented.

