# 0017-prd-homepage-search-and-airline-error

> **Scope of this document:** Items 3 and 4 from `25_Apr_Observations.md` only.
> Item 3 = Homepage manufacturer search missing autocomplete / fuzzy dropdown.
> Item 4 = Internal Server Error when accessing an aircraft from the global incidents list.

---

## 1. Introduction / Overview

Two distinct but related UX and reliability issues are blocking core user journeys on the Aircraft Safety Tracker:

**Item 3 – Homepage Search Incomplete Results**
The homepage search bar returns only a single result (e.g., "Boeing 727") when a user types a manufacturer name like "Boeing", despite many more models existing in the database. The root cause is that the `/search` route performs a correct `ILIKE` query but the results are grouped and rendered only as `AircraftVariant` entries; aircraft that have no variants are silently dropped from the output. Additionally, there is no autocomplete dropdown to guide users as they type.

**Item 4 – Internal Server Error on `/aircraft/<id>`**
Clicking an aircraft badge link in the global incidents list (`/incidents`) triggers a 500 Internal Server Error. The link is generated in `global_incident_list.html` as `url_for('main.aircraft_details', aircraft_id=incident.aircraft.id)`. The `aircraft_details` route wraps its body in a `try/except` that re-raises the exception, so any unhandled error inside (e.g., a broken relationship, a missing join, or a template rendering failure) surfaces as a 500 rather than a graceful 404 or error page.

---

## 2. Goals

1. The homepage search must return all matching `Aircraft` models, regardless of whether they have associated `AircraftVariant` rows.
2. The search results must be grouped by series (existing logic) and rendered correctly for both variant-backed and variant-less aircraft.
3. Accessing `/aircraft/<id>` with a valid ID must never return a 500; it must render the detail page or return a 404.
4. Accessing `/aircraft/<id>` with an invalid or non-existent ID must return a clean 404 page.
5. (Stretch) A lightweight autocomplete suggestion list should appear as the user types in the search bar, showing up to 8 matching model names.

---

## 3. User Stories

- As a user typing "Boeing" in the search bar, I want to see all Boeing aircraft models in the dropdown, not just one, so I can navigate to the model I'm looking for.
- As a user browsing the global incidents list, I want clicking an aircraft badge to take me to that aircraft's detail page without errors.
- As a user who navigates directly to `/aircraft/9999` (non-existent), I want to see a clear "Not Found" page, not a server error.

---

## 4. Functional Requirements

### 4.1 Homepage Search – Complete Results (Item 3)

**FR-3.1** The `/search` route must return all `Aircraft` records whose `model_name` matches the query (case-insensitive `ILIKE`), plus all `Aircraft` records that have at least one `AircraftVariant` whose `variant_name` matches.

**FR-3.2** The grouping logic (series extraction from `model_name`) must be applied to every matched `Aircraft`, not only those that have variants.

**FR-3.3** When an `Aircraft` has no `AircraftVariant` rows, it must still appear in `grouped_results` as a direct `Aircraft` entry (the template already handles this branch at line 103–109 of `routes.py`; the bug is that the variant fetch loop at lines 83–97 silently skips aircraft with no variants, and the fallback at 99–109 only runs if `variants_by_series` is empty for that series — which it is not when other aircraft in the same series do have variants).

**FR-3.4** The `grouped_results` dict passed to `search_results.html` must contain every matched aircraft, either as an `AircraftVariant` item or as an `Aircraft` item, with no silent omissions.

**FR-3.5** (Stretch) The `/autocomplete` route (line 115–137 of `routes.py`) must return up to 8 suggestions and the frontend must display them in a dropdown anchored below the search input, dismissible on outside click or Escape key.

### 4.2 Aircraft Detail Page – No 500 Errors (Item 4)

**FR-4.1** `aircraft_details(aircraft_id)` must use `db.get_or_404(Aircraft, aircraft_id)` (already present) and must not re-raise unhandled exceptions as 500s.

**FR-4.2** The `except Exception` block must log the error and return a rendered 500 error page (or redirect to 404 if the record is genuinely missing), never a bare Python traceback.

**FR-4.3** The template `aircraft.html` must not assume any relationship is non-empty; all dynamic relationship accesses (`.variants.all()`, `.incidents`, `.system_tags`) must be guarded or handled gracefully.

**FR-4.4** The link in `global_incident_list.html` (line 24) must only render the aircraft badge anchor when `incident.aircraft` is not `None` (already guarded by `{% if incident.aircraft %}`). Confirm this guard is present and correct.

**FR-4.5** The `aircraft_details` route must return HTTP 404 for any `aircraft_id` that does not exist in the `aircraft` table.

---

## 5. Non-Goals (Out of Scope)

- Implementing full fuzzy/trigram search (pg_trgm) — the existing `ILIKE` is sufficient for this fix.
- Creating dedicated "Airline" model pages or a separate airline entity.
- Changing the visual design of the search results dropdown.
- Fixing NTSB model mismatch or broken PDF links (Items 1 and 2 of the observations — separate PRD).
- Pagination of search results.

---

## 6. Technical Analysis

### 6.1 Root Cause – Item 3

In `routes.py` `/search` (lines 83–113):

```
# Step 1: fetch all variants for matched aircraft
variants_by_series = {}
for variant in AircraftVariant.query.filter(
    AircraftVariant.aircraft_id.in_([a.id for a in results])
).all():
    series_name = aircraft_to_series.get(variant.aircraft_id)
    ...
    grouped_results[series_name].append(variant)

# Step 2: fallback — add aircraft directly if no variants found for that series
for aircraft in results:
    series_name = aircraft_to_series.get(aircraft.id) or aircraft.model_name
    if series_name not in grouped_results:          # <-- BUG: only adds if series absent
        grouped_results[series_name].append(aircraft)
```

The fallback condition `if series_name not in grouped_results` means: if any other aircraft in the same series already added a variant entry, the variant-less aircraft is silently dropped. Fix: always add the aircraft as a fallback entry if it has no variants of its own in `grouped_results`.

### 6.2 Root Cause – Item 4

In `routes.py` `aircraft_details` (lines 211–260):

```python
try:
    aircraft = db.get_or_404(Aircraft, aircraft_id)
    ...
    return render_template('aircraft.html', ...)
except Exception as e:
    logger.exception("Error rendering aircraft_details ...")
    raise   # <-- re-raises as 500
```

The `raise` at the end converts any rendering error into a 500. The fix is to return a proper error response instead of re-raising. Additionally, the `apply_source_priority_order` join and the `aircraft.variants.all()` call can fail if the ORM session is in a bad state or if the query produces unexpected results.

### 6.3 Affected Files

| File | Change needed |
|---|---|
| `app/routes.py` | Fix search grouping logic (FR-3.3/3.4); fix `aircraft_details` exception handler (FR-4.2) |
| `app/templates/components/search_results.html` | Verify both `AircraftVariant` and `Aircraft` item branches render correctly |
| `app/templates/components/global_incident_list.html` | Confirm `{% if incident.aircraft %}` guard is present |
| `app/templates/aircraft.html` | Confirm no unguarded relationship accesses |

---

## 7. Acceptance Criteria

### Item 3 – Search

| # | Criterion |
|---|---|
| AC-3.1 | Searching "Boeing" returns more than one series group in the dropdown. |
| AC-3.2 | An `Aircraft` with zero `AircraftVariant` rows appears in search results when its `model_name` matches the query. |
| AC-3.3 | An `Aircraft` with variants appears in search results grouped under the correct series. |
| AC-3.4 | No `Aircraft` that matches the query is silently omitted from `grouped_results`. |
| AC-3.5 | The search result template renders without Jinja2 errors for both `AircraftVariant` items and `Aircraft` items. |

### Item 4 – Aircraft Detail

| # | Criterion |
|---|---|
| AC-4.1 | `GET /aircraft/<valid_id>` returns HTTP 200 for every aircraft in the database. |
| AC-4.2 | `GET /aircraft/<nonexistent_id>` returns HTTP 404 with the custom 404 template. |
| AC-4.3 | No request to `/aircraft/<id>` returns HTTP 500 under normal operating conditions. |
| AC-4.4 | Clicking an aircraft badge in the global incidents list navigates to the correct aircraft detail page. |
| AC-4.5 | If `aircraft_details` encounters an unexpected error, it logs the exception and returns a 500 error page (not a bare traceback), and the error is visible in application logs. |

---

## 8. Edge Cases

- **Aircraft with `total_incidents = 0` but actual `Incident` rows**: `aircraft_has_incidents()` queries the `Incident` table directly, so this is safe. The `total_incidents` counter is a denormalized cache and should not gate rendering.
- **`incident.aircraft` is `None`** (orphaned incidents with `aircraft_id = NULL`): The `global_incident_list.html` template already guards this with `{% if incident.aircraft %}`. Confirm the guard is present and the `else` branch renders `raw_model_variant`.
- **Search query with special characters** (e.g., `%`, `_`): The `ILIKE` query uses `f'%{query}%'` without escaping. This is a pre-existing issue; do not fix in this ticket but note it.
- **Very large `grouped_results`**: No pagination is in scope; limit results to 50 `Aircraft` records in the search query to prevent memory issues.
- **`aircraft_details` called with `aircraft_id = 0`**: `db.get_or_404` will return 404 correctly.
- **Concurrent summary job creation**: Not in scope for this ticket.

---

## 9. Success Metrics

- Zero 500 errors on `/aircraft/<id>` for any ID present in the database (verified by running the test suite and manual spot-check of 10 aircraft IDs).
- Search for "Boeing" returns ≥ 5 distinct series groups (assuming the database has been seeded with standard data).
- All existing tests in `tests/test_routes.py` continue to pass.
- New tests (see §10) pass.

---

## 10. Implementation Plan

### Phase 1 – Fix Search Grouping (Item 3)

**Step 1.1** In `routes.py` `/search`, replace the fallback loop (lines ~99–109) with logic that tracks which aircraft IDs already have a variant entry in `grouped_results`, and adds a direct `Aircraft` entry for any matched aircraft that does not:

```python
# Track which aircraft_ids already have a variant entry
aircraft_ids_with_variants = {v.aircraft_id for v in all_variants}

for aircraft in results:
    if aircraft.id not in aircraft_ids_with_variants:
        series_name = aircraft_to_series.get(aircraft.id) or aircraft.model_name
        if series_name not in grouped_results:
            grouped_results[series_name] = []
        grouped_results[series_name].append(aircraft)
```

**Step 1.2** Verify `search_results.html` renders both `AircraftVariant` items (using `item.aircraft_id`) and `Aircraft` items (using `item.id`) without error. The template already has both branches (lines 37 and 47); confirm the `isinstance` or attribute check is correct.

**Step 1.3** Add a test in `tests/test_routes.py`:
- Create an `Aircraft` with no `AircraftVariant` rows.
- `GET /search?q=<model_name>` and assert the response contains the model name.

### Phase 2 – Fix Aircraft Detail 500 (Item 4)

**Step 2.1** In `routes.py` `aircraft_details`, replace `raise` in the `except` block with a proper error response:

```python
except Exception as e:
    logger.exception("Error rendering aircraft_details for aircraft_id=%s", aircraft_id)
    return render_template('500.html'), 500
```

If a `500.html` template does not exist, use the existing `404.html` pattern or Flask's default error handler.

**Step 2.2** Confirm `db.get_or_404` is called before any other database access in `aircraft_details` (it is, at line 212). No change needed here.

**Step 2.3** Audit `aircraft.html` for any unguarded relationship accesses that could raise `AttributeError` or `DetachedInstanceError`. Specifically check:
- `aircraft.variants.all()` — called in the route, result passed as `variant_options`; safe.
- `aircraft.incidents` — accessed via `query = aircraft.incidents`; safe as long as session is active.

**Step 2.4** Add tests in `tests/test_routes.py`:
- `GET /aircraft/<nonexistent_id>` → assert HTTP 404.
- `GET /aircraft/<valid_id>` for every aircraft fixture → assert HTTP 200.

### Phase 3 – Verify Global Incidents List Link (Item 4 supporting)

**Step 3.1** Read `global_incident_list.html` line 24 and confirm the `{% if incident.aircraft %}` guard wraps the anchor tag. If not, add it.

**Step 3.2** Add a test that creates an `Incident` with `aircraft_id = None` and asserts `GET /incidents` returns HTTP 200 without error.

### Phase 4 – Run Full Test Suite

```bash
PYTHONPATH=. pytest -q
```

All existing tests must pass. Fix any regressions before merging.

---

## 11. Testing Strategy

| Test | Type | File | Assertion |
|---|---|---|---|
| Search returns aircraft with no variants | Integration | `test_routes.py` | Response body contains model name |
| Search groups aircraft correctly by series | Integration | `test_routes.py` | `grouped_results` has ≥ 2 keys for multi-model manufacturer |
| `/aircraft/<valid_id>` returns 200 | Integration | `test_routes.py` | `status_code == 200` |
| `/aircraft/<nonexistent_id>` returns 404 | Integration | `test_routes.py` | `status_code == 404` |
| `/incidents` with null-aircraft incident returns 200 | Integration | `test_routes.py` | `status_code == 200` |
| No 500 on aircraft detail with minimal data | Integration | `test_routes.py` | `status_code == 200` for aircraft with 0 incidents |

---

## 12. Open Questions

1. Does a `500.html` template exist? If not, should we create a minimal one or reuse `404.html`?
2. Should the search result limit (currently 50 aircraft) be configurable via `config.py`?
3. Is the stretch autocomplete (FR-3.5) in scope for this sprint, or deferred?
