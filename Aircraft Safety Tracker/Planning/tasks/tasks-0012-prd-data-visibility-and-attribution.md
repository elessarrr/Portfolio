## Relevant Files

- `app/templates/aircraft.html` - Main aircraft detail page template, where the AI Summary card is rendered and incident listings are displayed.
- `app/templates/components/summary_card_polling.html` - HTMX component responsible for polling the AI summary status.
- `app/routes.py` - Adds SQL-level source priority ordering helper (`NTSB > FAA_AIDS > FAA_SDR > ASN`) for aircraft incident detail/list/export retrieval.
- `app/models.py` - Contains the `Aircraft` and `Incident` models, including `total_incidents` and `source_id`.
- `app/templates/components/incident_list.html` - Incident rows now show a clear "Primary Source" badge using NTSB > FAA_AIDS > FAA_SDR > ASN fallback logic.
- `tests/test_routes.py` - Adds regression coverage for source-priority ordering and visible "Primary Source" badge rendering.
- `app/static/css/styles.css` - For any new styling related to data source indicators or footer redesign.
- `app/templates/base.html` - Footer now renders normalized month-year freshness labels for each required source.
- `config.py` - Defines default month-year footer freshness labels via `DATA_FRESHNESS_DEFAULTS`.
- `app/context_processors.py` - Builds ordered footer freshness context entries (`ASN`, `FAA_AIDS`, `FAA_SDR`, `NTSB`) from import state plus config defaults.

### Notes
- The primary goal is to improve data clarity and user trust by ensuring accurate and relevant information is displayed.
- Conditional rendering in Jinja templates will be key for the AI Summary and data source indicators.
- Backend logic in `app/routes.py` will need careful modification to handle data source prioritization without breaking existing filters.
- 2.1 analysis findings:
  - `aircraft_details` and `get_incidents` query `Incident` rows directly with no source-priority ranking at query time.
  - `Incident` ↔ `IncidentSource` is one-to-many (`lazy='dynamic'`), and source prominence is currently determined in template logic, not SQL.
  - In `incident_list.html`, source chips are sorted by `source_name`, so non-priority ordering can dominate visual prominence.
  - `primary_source` currently special-cases NTSB, then falls back to first alphabetical source; this does not fully encode NTSB > FAA_AIDS > FAA_SDR > ASN.
  - `apply_incident_filters` joins `Incident.sources` for source filtering and can return incidents with multiple attached sources without any deterministic per-source precedence.

## Progress

- 🟡 In Progress — 92% complete (11/12 tasks checked)

## Tasks

- [x] 1.0 Implement Conditional AI Safety Summary Display
  - [x] 1.1 In `app/templates/aircraft.html`, add a Jinja `{% if aircraft.total_incidents > 0 %}` condition around the entire `AI Safety Summary` card component.
  - [x] 1.2 Ensure that if the card is hidden, the layout remains visually cohesive (no awkward gaps).
  - [x] 1.3 In `app/routes.py`, within the `aircraft_details` route, add a check to prevent initiating the AI summary generation job if `aircraft.total_incidents` is 0.

- [x] 2.0 Enhance Incident Data Source Prioritization and Display
  - [x] 2.1 Conduct a comprehensive analysis of `app/routes.py` (specifically `get_incidents` and `aircraft_details`) and `app/models.py` to understand how incident data is currently queried and displayed, and why other sources are not prominent.
  - [x] 2.2 Modify the incident query logic in `app/routes.py` to prioritize incidents based on NTSB > FAA_AIDS > FAA_SDR > ASN. This means if an incident exists in multiple sources, the highest priority one should be selected.
  - [x] 2.3 In `app/templates/aircraft.html` (or a relevant incident card component), add a small UI indicator (e.g., a badge or text label) next to each incident entry to clearly show its source (NTSB, FAA_AIDS, FAA_SDR, or ASN).
  - [x] 2.4 Ensure that existing filters (e.g., by manufacturer, date range) continue to function correctly with the new prioritization logic.

- [ ] 3.0 Redesign Footer for Unified Data Attribution
  - [x] 3.1 In `app/templates/base.html`, locate the existing footer section.
  - [x] 3.2 Replace the current attribution with the consolidated text: "Data sourced from below sources. Not affiliated with any manufacturer."
  - [x] 3.3 Clearly list all data sources (ASN, FAA_AIDS, FAA_SDR, NTSB) in the footer.
  - [x] 3.4 For each data source, add a "Data Freshness" indicator displaying the month and year of the last update (e.g., "ASN: Apr 2026"). This may require defining these dates in a `config.py` or similar file and passing them to the template.
  - [ ] 3.5 Apply appropriate CSS styling in `app/static/css/styles.css` to ensure the redesigned footer is visually prominent and clean.
