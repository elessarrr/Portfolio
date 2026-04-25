# Tasks: Homepage Search Fix and Aircraft Detail Error Handling

**PRD:** `0017-prd-homepage-search-and-airline-error.md`  
**Status:** `25%` (1/4 parent tasks in progress)

| Step | Status | Notes |
|---|---|---|
| 1. Fix `/search` grouping bug — Aircraft without variants dropped silently | 🔄 In Progress | Updated fallback logic; template branch verified; search test added |
| 2. Fix `/aircraft/<id>` bare `raise` exception handler | ⬜ | |
| 3. Audit template guards and verify existing protections | ┍ Partial — `global_incident_list.html` already has `{% if incident.aircraft %}` guard | |
| 4. Add tests and run full suite | ⬜ | |

---

## Relevant Files

- `app/routes.py` — Fix search grouping logic (Step 1.1) and replace bare `raise` in `aircraft_details` (Step 2.1).
- `app/templates/components/search_results.html` — Verify Aircraft item branch renders correctly (Step 1.2).
- `app/templates/components/global_incident_list.html` — Already has `{% if incident.aircraft %}` guard; confirm it covers the anchor tag (Step 3.1).
- `app/templates/aircraft.html` — Audit for unguarded relationship accesses (Step 3.2).
- `tests/test_routes.py` — Add tests for search grouping fix and aircraft detail error handling.
- `tests/test_search.py` — If exists, add tests here; otherwise add to `test_routes.py`.

### Notes

- The search bug: the fallback loop that adds Aircraft directly runs only when `not variants` (global zero-variant check). If any aircraft in a series has a variant, the fallback is skipped and variant-less Aircraft are silently dropped.
- The aircraft detail bug: `except Exception` block ends with bare `raise`, converting any template/ORM rendering error into HTTP 500. Fix: return a proper response instead.
- No `500.html` template exists — use the Flask default error mechanism or the existing `@bp.app_errorhandler(404)` pattern.
- Use `PYTHONPATH=. pytest tests/test_routes.py` to run targeted tests.
- The search query uses `ILIKE` without escaping special SQL characters (`%`, `_`) — pre-existing issue noted but not in scope.
- Limit: `Aircraft.query...limit(50)` already exists; no pagination change needed.

---

## Tasks

- [ ] 1.0 Fix `/search` grouping bug — Aircraft records without variants silently dropped
  - [x] 1.1 In `app/routes.py` `/search`, update the fallback loop to track which aircraft IDs already have a variant entry in `grouped_results`, and add a direct `Aircraft` entry for each aircraft that has no variant in `grouped_results` — regardless of whether other aircraft in the same series have variants
  - [x] 1.2 Verify `app/templates/components/search_results.html` correctly renders both `AircraftVariant` items (uses `item.aircraft_id`) and bare `Aircraft` items (uses `item.id`) — both branches are already present in the template; confirm the `{% if item.variant_name is defined %}` conditional correctly distinguishes them
  - [x] 1.3 Add an integration test in `tests/test_routes.py`: create an `Aircraft` with no `AircraftVariant` rows and whose `model_name` matches the search query; assert the response HTML contains the model name
  - [ ] 1.4 Run targeted search tests and confirm the fix works end-to-end

- [ ] 2.0 Fix `/aircraft/<id>` bare `raise` exception handler
  - [ ] 2.1 In `app/routes.py` `aircraft_details`, replace the bare `raise` in the `except Exception` block with a proper error response — either render a Flask error page or use the existing `@bp.app_errorhandler(404)` pattern
  - [ ] 2.2 Audit whether a `500.html` error template is needed — check if one exists in `app/templates/`; if not, use `render_template('aircraft.html', aircraft=None)` to reuse the existing page shell with an error state, or use `abort(500)` from flask.wrappers
  - [ ] 2.3 Add an integration test in `tests/test_routes.py`: `GET /aircraft/<valid_id>` → `status_code == 200` for an aircraft with minimal/edge-case data (zero incidents, no variants); `GET /aircraft/<nonexistent_id>` → `status_code == 404` — confirm both already work via `db.get_or_404` and the fixed exception handler
  - [ ] 2.4 Run targeted aircraft detail tests

- [ ] 3.0 Audit template guards for aircraft detail and search results rendering
  - [ ] 3.1 Confirm `app/templates/components/global_incident_list.html` wraps the aircraft badge anchor with `{% if incident.aircraft %}` — already present at line 24; verify the entire badge anchor (not just the href) is inside the guard
  - [ ] 3.2 Audit `app/templates/aircraft.html` for unguarded relationship accesses (`.variants.all()`, `.incidents`, `.system_tags`); confirm all are either accessed safely in the route (with null guards) or in templates with `{% if ... %}` conditionals
  - [ ] 3.3 Verify the search results template (`search_results.html`) handles both `item.aircraft_id` (AircraftVariant path) and `item.id` (Aircraft path) correctly — no Jinja2 `UndefinedError` possible for these accesses
  - [ ] 3.4 Add a test in `tests/test_routes.py`: create an `Incident` with `aircraft_id = None`; `GET /incidents` → `status_code == 200` with no errors rendered in HTML

- [ ] 4.0 Add regression tests and run full test suite
  - [ ] 4.1 Add test: search "Boeing" returns ≥ 2 distinct series groups when multiple Boeing models exist
  - [ ] 4.2 Add test: search returns Aircraft records that have no variants but match the query string
  - [ ] 4.3 Add test: `GET /aircraft/<id>` for a valid ID returns 200 (verify with an in-test fixture aircraft)
  - [ ] 4.4 Add test: `GET /aircraft/<id>` for a non-existent ID returns 404
  - [ ] 4.5 Run full test suite: `PYTHONPATH=. pytest tests/test_routes.py -q` — all existing tests must pass
  - [ ] 4.6 Run full project test suite: `PYTHONPATH=. pytest tests/ -q` — confirm no regressions
