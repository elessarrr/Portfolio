## Relevant Files

- `app/templates/components/stats_grid.html` - Contains the 'Years in Service' card that needs to be removed.
- `app/templates/aircraft.html` - Contains the main layout for the aircraft detail page. Needs to be checked for the 'AI Analysis' card components and to ensure the grid layout adjusts smoothly.
- `app/static/js/main.js` - May contain event listeners related to the 'AI Analysis' form that need to be cleaned up.

### Notes
- We are specifically instructed *not* to delete the backend API endpoints (`/api/analyze-report`) or any python service files (`gemini.py`, `deepseek.py`, `report_analyzer.py`). We are only touching frontend code (HTML/Jinja/JS).
- We must ensure that the CSS Grid or Flexbox container that held these cards expands the remaining cards gracefully so no empty "holes" are left in the layout.

## Tasks

- [x] 1.0 Remove 'Years in Service' UI Component
  - [x] 1.1 Open `app/templates/components/stats_grid.html` (or wherever the stats cards are located).
  - [x] 1.2 Locate the HTML `<div>` block that renders the 'Years in Service' label and data (`aircraft.years_in_service`).
  - [x] 1.3 Delete the entire HTML block for the 'Years in Service' card.

- [x] 2.0 Remove 'AI Analysis' UI Component
  - [x] 2.1 Open `app/templates/aircraft.html`.
  - [x] 2.2 Locate the HTML block that renders the 'AI Analysis' card (including the input form and submit button).
  - [x] 2.3 Delete the entire HTML block for the 'AI Analysis' card.
  - [x] 2.4 Open `app/static/js/main.js` and remove any JavaScript event listeners or functions associated with submitting the 'AI Analysis' form (e.g., listeners attached to the "Analyze Report" button).

- [x] 3.0 Adjust Layout and Verify Backend Integrity
  - [x] 3.1 In `app/templates/aircraft.html` or `stats_grid.html`, inspect the parent container classes for the remaining cards.
  - [x] 3.2 Adjust CSS classes (e.g., Tailwind classes like `grid-cols-3` to `grid-cols-2` or `auto-fit`) to ensure the remaining UI components stretch or align cleanly to fill the newly available space.
  - [x] 3.3 Verify that no backend files (`app/models.py`, `app/routes.py`, `app/services/report_analyzer.py`) were modified during this process.