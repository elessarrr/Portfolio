## Relevant Files

- `app/templates/components/incident_list.html` - Incident table/list component with adjusted table container/padding to keep spacing balanced without thumbnails.
- `app/templates/components/global_incident_list.html` - Global incident card component now includes truncated description markup and an inline "Read more" control.
- `app/static/css/styles.css` - Contains `.line-clamp-3` and `.dashboard-charts` responsive grid rules for consistent chart card widths.
- `app/static/js/main.js` - Contains delegated vanilla JS for "Read more / Read less" toggling on truncated incident descriptions.
- `app/templates/incidents_database.html` - Dashboard container updated to use chart-grid wrapper class for consistent chart sizing behavior.
- `app/templates/components/global_charts.html` - Chart cards now render in `.dashboard-charts` with equal-width responsive grid behavior.
- `app/templates/aircraft.html` - Aircraft filters now conditionally render `System Tags`, `Variants`, and `Data Sources` sections only when options exist.
- `app/templates/components/stats_grid.html` - Years in Service stat card now renders only when value is present and not `"Unknown"`.
- `app/services/report_analyzer.py` - Contains the logic for interacting with DeepSeek/Gemini. We need to review the timeout and exception handling here to ensure the AI summary doesn't hang indefinitely.
- `app/routes.py` - Summary status polling now checks failed jobs and returns `summary_card` error state instead of continuing polling.
- `app/templates/components/summary_card_polling.html` - Polling card now renders explicit failure messaging and disables polling when summary generation fails.
- `app/templates/base.html` - The global layout where we will add the global error toast container and the global HTMX loading indicator styles.

## Progress

- 🟡 In Progress — 65% complete (15/23 tasks checked)

### Notes
- The application relies heavily on HTMX for interactivity. Ensure that any new error messages or loading states utilize HTMX attributes (like `htmx-indicator` and `hx-on::after-request`) rather than writing custom AJAX logic.
- When modifying Jinja templates (`{% if %}`), test edge cases (empty lists, None values, "Unknown" strings) to ensure sections hide correctly.

## Tasks

- [x] 1.0 UI Polish & Asset Cleanup
  - [x] 1.1 Remove `<img>` tags (or image placeholder divs) entirely from incident cards in `incident_list.html` and `global_incident_list.html`.
  - [x] 1.2 Adjust flexbox/padding on incident cards to ensure the layout looks balanced without the image thumbnail on the left.
  - [x] 1.3 Add `.line-clamp-3` or similar CSS rules in `styles.css` to truncate incident descriptions.
  - [x] 1.4 Add a `<button>` or `<a>` tag with "Read more" directly after the truncated text.
  - [x] 1.5 Write a vanilla JS function in `main.js` to toggle the CSS class on the description container when "Read more" is clicked, expanding it to full height.
  - [x] 1.6 Update the `.dashboard-charts` container in `incidents_database.html` (and associated CSS) to use CSS Grid (`grid-template-columns: repeat(auto-fit, minmax(300px, 1fr))`) so the manufacturer and severity charts have consistent widths.

- [x] 2.0 Dynamic Data Display
  - [x] 2.1 In `aircraft.html`, wrap the "System Tags" filter section in a Jinja `{% if system_options %}` block so it only renders if there are tags.
  - [x] 2.2 Wrap the "Variants" filter section in an `{% if variant_options %}` block.
  - [x] 2.3 Wrap the "Sources" filter section in an `{% if source_options %}` block.
  - [x] 2.4 Update the "Years in Service" display block in `aircraft.html` to `{% if aircraft.years_in_service and aircraft.years_in_service != 'Unknown' %}` so it hides completely when invalid.

- [ ] 3.0 AI Summary Backend Fixes
  - [x] 3.1 Audit `process_pending_summary_job` in `routes.py` to ensure all exceptions from `DeepSeekService` and `GeminiService` are caught and that `job.status` is strictly set to 'failed'.
  - [x] 3.2 Verify that `check_summary_status` in `routes.py` checks for 'failed' job statuses and returns an error template rather than continuing to return `summary_card_polling.html`.
  - [x] 3.3 Update `summary_card_polling.html` to display a clear error message (e.g., "Failed to generate summary. Please try again later.") if the backend indicates a failure.
  - [ ] 3.4 Add an explicit timeout parameter to the `client.chat.completions.create` call in `DeepSeekAnalyzerAdapter` (and Gemini equivalent) to prevent hanging connections.

- [ ] 4.0 Global Feedback States
  - [ ] 4.1 Add an `#htmx-global-indicator` element to `base.html` (e.g., a slim progress bar at the top of the screen) and style it in `styles.css`.
  - [ ] 4.2 Add `hx-indicator="#htmx-global-indicator"` to the search input in `index.html` and `base.html`.
  - [ ] 4.3 Add `hx-indicator` to the "Apply Filters" buttons so users know the list is updating.
  - [ ] 4.4 Add a hidden `#toast-container` to `base.html`.
  - [ ] 4.5 Write a small JS listener in `main.js` that listens for `htmx:responseError` and `htmx:sendError` events, and triggers a visual error toast in the `#toast-container`.
