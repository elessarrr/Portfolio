## Relevant Files

- `scripts/scrape_boeing.py` - Will need to be updated or re-run to pull the full catalog of Boeing models from ASN to replace the truncated file.
- `app/routes.py` - Needs a new `/incidents` route to serve the main page and an `/incidents/page` endpoint to return HTML fragments for infinite scroll.
- `app/templates/incidents_database.html` - New template for the comprehensive database page with filters and charts.
- `app/templates/components/global_incident_list.html` - New or adapted component to render the infinite scroll list of incidents across all models.
- `app/static/js/charts.js` - A new JS file to handle rendering Chart.js or similar visualizations based on data attributes or JSON endpoints.
- `tests/test_routes.py` - Needs new tests for the `/incidents` page, ensuring filters work globally and pagination returns the correct subset of data.

### Notes

- Unit tests should typically be placed alongside the code files they are testing, or in the `tests/` directory for Python/Flask apps.
- Use `pytest` to run tests.

## Tasks

- [x] 1.0 Data Ingestion & Resolution (Boeing Backfill)
  - [x] 1.1 Fix or re-run `scripts/scrape_boeing.py` to ensure it successfully scrapes the entire ASN Boeing index (737, 747, 777, etc.).
  - [x] 1.2 Verify the new `boeing_incidents.json` contains complete data (no truncation) and save it to `data/raw/`.
  - [x] 1.3 Run `flask import-data all` (or equivalent manual import) to ingest the new JSON and backfill the database with the missing models.
  - [x] 1.4 Ensure the deduplication pipeline (`app/ingestion/dedupe.py`) successfully merges the new ASN records with existing NTSB/FAA records.
- [x] 2.0 Backend Infrastructure for Incidents Database
  - [x] 2.1 Create a new `GET /incidents` route in `app/routes.py` that queries the `Incident` table globally (joining `Aircraft`).
  - [x] 2.2 Refactor `apply_incident_filters` in `app/routes.py` (if necessary) so it can apply filters (year range, severity, model) to a global query instead of just an aircraft-specific query.
  - [x] 2.3 Implement pagination logic in a new endpoint (e.g., `GET /incidents/page`) that accepts a page number and returns a limited chunk of incidents (e.g., 50 per page).
- [x] 3.0 Incidents Database Page UI & Infinite Scroll
  - [x] 3.1 Create `app/templates/incidents_database.html` with a layout supporting a sidebar for filters and a main content area for charts and the incident list.
  - [x] 3.2 Create `app/templates/components/global_incident_list.html` to render the rows of incidents.
  - [x] 3.3 Implement HTMX infinite scroll on the last element of the list (`hx-get="/incidents/page?page=2" hx-trigger="revealed" hx-swap="afterend"`).
- [x] 4.0 Filtering & Search Capabilities
  - [x] 4.1 Add a filter sidebar to `incidents_database.html` with inputs for: Year Range, Aircraft Manufacturer/Model, Incident Severity, and Geographical Location.
  - [x] 4.2 Wire the filter form using HTMX (`hx-get="/incidents" hx-target="#incident-container" hx-trigger="change"`) so changing a filter resets the list to page 1 and applies the new criteria.
  - [x] 4.3 Ensure the backend pagination endpoint (`/incidents/page`) respects the currently active filters passed in the query string.
- [ ] 5.0 Data Visualizations (Charts & Graphs)
  - [ ] 5.1 Add a lightweight charting library (e.g., Chart.js) to the project via CDN or NPM.
  - [ ] 5.2 Create an endpoint or inject JSON data into the template that aggregates incidents by Year, Severity, and System/Root Cause.
  - [ ] 5.3 Implement the "Timeline Trends" chart (Incidents per year).
  - [ ] 5.4 Implement the "Severity Breakdown" chart (Fatal vs. Non-fatal).
  - [ ] 5.5 Ensure the charts dynamically re-render (using JS or HTMX out-of-band swaps) whenever the user changes the active filters.