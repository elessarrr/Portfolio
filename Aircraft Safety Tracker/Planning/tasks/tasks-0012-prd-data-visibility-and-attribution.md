## Relevant Files

- `app/templates/aircraft.html` - Main aircraft detail page template, where the AI Summary card is rendered and incident listings are displayed.
- `app/templates/components/summary_card_polling.html` - HTMX component responsible for polling the AI summary status.
- `app/routes.py` - `aircraft_details` now gates AI summary generation eligibility with `aircraft.total_incidents > 0` (plus incident existence check).
- `app/models.py` - Contains the `Aircraft` and `Incident` models, including `total_incidents` and `source_id`.
- `app/static/css/styles.css` - For any new styling related to data source indicators or footer redesign.
- `app/templates/base.html` - The base template where the footer is defined.
- `config.py` (or similar) - May need a place to store data freshness dates.

### Notes
- The primary goal is to improve data clarity and user trust by ensuring accurate and relevant information is displayed.
- Conditional rendering in Jinja templates will be key for the AI Summary and data source indicators.
- Backend logic in `app/routes.py` will need careful modification to handle data source prioritization without breaking existing filters.

## Progress

- 🟡 In Progress — 25% complete (3/12 tasks checked)

## Tasks

- [ ] 1.0 Implement Conditional AI Safety Summary Display
  - [x] 1.1 In `app/templates/aircraft.html`, add a Jinja `{% if aircraft.total_incidents > 0 %}` condition around the entire `AI Safety Summary` card component.
  - [x] 1.2 Ensure that if the card is hidden, the layout remains visually cohesive (no awkward gaps).
  - [x] 1.3 In `app/routes.py`, within the `aircraft_details` route, add a check to prevent initiating the AI summary generation job if `aircraft.total_incidents` is 0.

- [ ] 2.0 Enhance Incident Data Source Prioritization and Display
  - [ ] 2.1 Conduct a comprehensive analysis of `app/routes.py` (specifically `get_incidents` and `aircraft_details`) and `app/models.py` to understand how incident data is currently queried and displayed, and why other sources are not prominent.
  - [ ] 2.2 Modify the incident query logic in `app/routes.py` to prioritize incidents based on NTSB > FAA_AIDS > FAA_SDR > ASN. This means if an incident exists in multiple sources, the highest priority one should be selected.
  - [ ] 2.3 In `app/templates/aircraft.html` (or a relevant incident card component), add a small UI indicator (e.g., a badge or text label) next to each incident entry to clearly show its source (NTSB, FAA_AIDS, FAA_SDR, or ASN).
  - [ ] 2.4 Ensure that existing filters (e.g., by manufacturer, date range) continue to function correctly with the new prioritization logic.

- [ ] 3.0 Redesign Footer for Unified Data Attribution
  - [ ] 3.1 In `app/templates/base.html`, locate the existing footer section.
  - [ ] 3.2 Replace the current attribution with the consolidated text: "Data sourced from below sources. Not affiliated with any manufacturer."
  - [ ] 3.3 Clearly list all data sources (ASN, FAA_AIDS, FAA_SDR, NTSB) in the footer.
  - [ ] 3.4 For each data source, add a "Data Freshness" indicator displaying the month and year of the last update (e.g., "ASN: Apr 2026"). This may require defining these dates in a `config.py` or similar file and passing them to the template.
  - [ ] 3.5 Apply appropriate CSS styling in `app/static/css/styles.css` to ensure the redesigned footer is visually prominent and clean.
