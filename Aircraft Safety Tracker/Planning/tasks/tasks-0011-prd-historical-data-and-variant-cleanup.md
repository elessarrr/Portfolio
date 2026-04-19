## Relevant Files

- `app/templates/aircraft.html` - Variant Comparison removed; layout flow reviewed to keep Stats/AI Summary/Incident Feed spacing cohesive.
- `app/routes.py` - Contains the `aircraft_details`, `get_incidents`, and `export_incidents_csv` routes where the hardcoded 1985 date filter logic must be removed.
- `tests/test_routes.py` - Adds regression coverage confirming `date_from` request filtering still applies to incident list and CSV export routes.

### Notes
- The goal is to ensure older aircraft correctly display their full historical data by default, while ensuring user-applied date filters still function as intended.
- Pay attention to potential null or malformed dates in older data when removing the backend filters. Ensure sorting logic (`order_by`) can handle these edge cases without crashing.

## Progress

- 🟡 In Progress — 71% complete (10/14 tasks checked)

## Tasks

- [x] 1.0 Remove Variant Comparison UI Component
  - [x] 1.1 Open `app/templates/aircraft.html`.
  - [x] 1.2 Locate the HTML section containing the "Variant Comparison" header and the grid of variant cards.
  - [x] 1.3 Delete the entire HTML block for the "Variant Comparison" section.
  - [x] 1.4 Review the layout to ensure the transition from the top stats grid directly into the Incident Feed (or AI Summary) looks visually cohesive without awkward spacing.

- [ ] 2.0 Remove Hardcoded Date Filters from Backend Routes
  - [x] 2.1 Open `app/routes.py`.
  - [x] 2.2 In the `aircraft_details` route, locate the `query.filter(Incident.date >= datetime(1985, 1, 1).date())` condition applied when `date_from` is absent. Remove this hardcoded fallback.
  - [x] 2.3 In the `get_incidents` route, locate and remove the identical `1985` date filter logic.
  - [x] 2.4 In the `export_incidents_csv` route, locate and remove the identical `1985` date filter logic.
  - [x] 2.5 Ensure that `apply_incident_filters` (or equivalent logic) still correctly applies a user-defined "From Date" if provided via the request arguments.

- [ ] 3.0 Verify Query Performance and User Date Filtering
  - [ ] 3.1 Verify that the removal of the 1985 filter does not cause excessive load times for aircraft with many incidents. Ensure the existing `limit(50)` or pagination mechanisms are functioning correctly on the detail page.
  - [ ] 3.2 Verify that the `order_by(Incident.date.desc())` sorting logic handles null or malformed dates (which might be more common in pre-1985 records) without throwing exceptions.
