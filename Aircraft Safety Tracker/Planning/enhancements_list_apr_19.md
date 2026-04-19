# Enhancements Opportunities - 19 Apr 2026

## UI/UX Improvements & Features

- [ ] **Variant Comparison Section** - Make the variant cards clickable so they route the user directly to the specific model/variant data shown on the card.
  - *Technical Feasibility Note:* This is highly feasible! We can make the cards act as quick-filters. Clicking a variant card (like "Boeing 247 D") can instantly append `?variant=Boeing 247 D` to the current URL, which will automatically filter the incident feed below it via HTMX to only show that specific variant's history.
  - *Fallback:* If we decide against implementing this click-through filtering logic, we should remove the entire 'Variant Comparison' section from the UI, as having non-interactive stat cards can be confusing for users.

- [ ] **Fix Missing Historical Incidents (e.g., Boeing 40)** - Older aircraft (like the Boeing 40) show zero incidents on their main detail page and incident feed, despite their Variant Comparison cards correctly showing historical incident counts (e.g., 40 B-4 has 14 incidents). Ticking the variant filter box does not resolve this.
  - *Root Cause Analysis:* The Variant Comparison cards pull from a pre-calculated database column (`AircraftVariant.total_incidents`) which correctly includes all historical data. However, the `aircraft_details` route in `app/routes.py` contains a hardcoded default filter that silently strips out all incidents before 1985 (`query.filter(Incident.date >= datetime(1985, 1, 1).date())`) if no `date_from` parameter is supplied. Older versions of this app did not enforce this arbitrary 1985 cutoff, which is why it worked correctly in the original portfolio repo.
  - *Solution:* Remove the hardcoded 1985 default date filter from `app/routes.py` (lines 192-193 and 242-243), or dynamically set the default date filter based on the earliest recorded incident for the specific aircraft being viewed.