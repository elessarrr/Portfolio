## Overall Progress: 0% (0/4 phases done)

| Phase | Status | Description |
|---|---|---|
| 1 | 🔲 Pending | Enhance Homepage Aircraft Model Table Comprehensiveness |
| 2 | 🔲 Pending | Resolve Internal Server Error on Aircraft Details Page |
| 3 | 🔲 Pending | Identify and Correct Misconfigured "Airline" Links |
| 4 | 🔲 Pending | Add/Adjust Tests for Homepage Table and Aircraft Details Error Handling |

## Relevant Files

- `app/routes.py` - Contains the `search()` function (for homepage table) and `aircraft_details()` route.
- `app/models.py` - Defines `Aircraft`, `AircraftVariant`, `Incident`, `IncidentSource` models.
- `app/templates/index.html` - Homepage template, renders the aircraft table.
- `app/templates/components/search_results.html` - Component for rendering the aircraft table.
- `app/templates/aircraft.html` - Aircraft details page template.
- `app/templates/404.html` - Custom 404 error page.
- `tests/test_routes.py` - Existing tests for routes, will need additions for new functionality and error handling.

### Notes

- The `search()` function in `app/routes.py` is currently used to populate the homepage table, not just the search bar.
- The `limit(20)` in `search()` is likely restricting the number of models displayed on the homepage.
- The `aircraft_details()` route expects an `aircraft_id` (integer) and fetches an `Aircraft` object.
- The "airline links" causing 500 errors need to be traced to their origin.

## Tasks

- [ ] 1.0 Enhance Homepage Aircraft Model Table Comprehensiveness
- [ ] 2.0 Resolve Internal Server Error on Aircraft Details Page
- [ ] 3.0 Identify and Correct Misconfigured "Airline" Links
- [ ] 4.0 Add/Adjust Tests for Homepage Table and Aircraft Details Error Handling
