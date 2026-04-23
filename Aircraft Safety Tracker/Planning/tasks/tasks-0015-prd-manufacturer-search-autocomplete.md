## Relevant Files

- `app/routes.py` - Where the new `/api/search/autocomplete` endpoint will be added to handle the search queries.
- `app/models.py` - Contains the `Aircraft` model with `full_name` and `make_model` columns that will be queried for autocomplete.
- `app/templates/index.html` - The main homepage template containing the search input field where autocomplete needs to be integrated.
- `app/static/js/main.js` - Where the frontend JavaScript logic for handling input events, displaying the dropdown, and managing user interaction will be added.
- `app/static/css/styles.css` - Where CSS classes for the autocomplete dropdown styling (border, shadow, hover states) will be added.
- `tests/test_routes.py` - Route tests for autocomplete JSON payload shape and result cap behavior.

### Notes
- Leverages the existing PostgreSQL `pg_trgm` fuzzy matching infrastructure already used by the main search.
- The autocomplete endpoint should be lightweight and fast, returning only essential fields (e.g., `id`, `make_model`, `full_name`) to minimize payload size.
- Ensure the dropdown has proper z-index and positioning to appear above other page elements.

## Status Tracker

- Progress: `🟩🟩🟩⬜⬜⬜⬜⬜ 29%` (6/21 tasks complete, including parent tasks)
- Active Parent Task: `2.0`
- Last Completed Parent Task: `1.0`

## Tasks

- [x] 1.0 Create Autocomplete Backend API Endpoint
  - [x] 1.1 In `app/routes.py`, add a new route decorator for `/api/search/autocomplete`.
  - [x] 1.2 Implement the route handler to accept a `q` query parameter.
  - [x] 1.3 Write a SQLAlchemy query using `ILIKE` or `pg_trgm` fuzzy matching against the `Aircraft` model's `full_name` or `make_model` columns.
  - [x] 1.4 Limit the query results to 5 matches.
  - [x] 1.5 Return the results as JSON (e.g., `{"results": [{"id": 1, "make_model": "Boeing 737-800"}, ...]}`).

- [ ] 2.0 Implement Frontend Autocomplete UI and Logic
  - [ ] 2.1 In `app/templates/index.html`, locate the search input field and add a wrapper `div` with `position: relative` to contain the dropdown.
  - [ ] 2.2 In `app/static/js/main.js`, add an event listener for the `input` event on the search field.
  - [ ] 2.3 Implement a debounce function (e.g., 200ms delay) to avoid excessive API calls while typing.
  - [ ] 2.4 On valid input (2+ characters), fetch data from `/api/search/autocomplete?q=<query>`.
  - [ ] 2.5 Dynamically render a `<ul>` dropdown below the input containing up to 5 suggestions.
  - [ ] 2.6 Add a click handler to each suggestion to navigate to `/aircraft/<id>`.
  - [ ] 2.7 Add an event listener on `keydown` (Escape) and `blur`/`click` on the document to close the dropdown when appropriate.
  - [ ] 2.8 In `app/static/css/styles.css`, add styling for the autocomplete dropdown (border, shadow, hover states, z-index).

- [ ] 3.0 Test and Polish
  - [ ] 3.1 Manually test typing 2+ characters (e.g., "737") and verify the dropdown appears with matching suggestions.
  - [ ] 3.2 Verify clicking a suggestion navigates to the correct aircraft detail page.
  - [ ] 3.3 Test that the dropdown disappears on Escape key press.
  - [ ] 3.4 Test that the dropdown disappears when clicking outside the search area.
  - [ ] 3.5 Verify the dropdown handles edge cases (e.g., no results, special characters, very long input).
