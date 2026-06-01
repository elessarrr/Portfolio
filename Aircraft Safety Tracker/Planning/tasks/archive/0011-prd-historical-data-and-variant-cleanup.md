# 0011-prd-historical-data-and-variant-cleanup

## 1. Introduction/Overview
The Aircraft Safety Tracker application currently suffers from two distinct data presentation issues on the aircraft detail pages, as noted in the April 19th enhancements list. First, the "Variant Comparison" section displays static statistics but is non-interactive, leading to user confusion. Second, historical aircraft (like the Boeing 40) display zero incidents in their feed despite having recorded historical crashes, due to an arbitrary backend date filter. This PRD addresses both issues by removing the confusing UI component and fixing the underlying query logic to ensure data accuracy across all eras of aviation.

## 2. Goals
*   **Improve UX Clarity:** Remove the non-interactive "Variant Comparison" section entirely to prevent users from attempting to click unresponsive data cards.
*   **Restore Data Accuracy:** Ensure the incident feed and summary statistics correctly reflect *all* historical data for an aircraft, regardless of the era it flew in.
*   **Maintain Existing Functionality:** Ensure the standard sidebar filters (including variant checkboxes) continue to work correctly after the date filter changes.

## 3. User Stories
*   **As a user**, I want to view the incident history of vintage aircraft (like the Boeing 40) so that I can understand their complete safety record without arbitrary date cutoffs hiding the data.
*   **As a user**, I don't want to see static "Variant Comparison" cards that look clickable but do nothing, so that the interface feels intuitive and responsive.

## 4. Functional Requirements

1.  **Remove Variant Comparison UI:** Delete the HTML/Jinja template code that renders the entire "Variant Comparison" section (including the section header and the grid of variant cards) from the aircraft detail page.
2.  **Remove Default Date Filter (Detail Route):** In `app/routes.py`, locate the `aircraft_details` route (around line 180). Remove the hardcoded `query.filter(Incident.date >= datetime(1985, 1, 1).date())` logic that applies when no `date_from` parameter is present.
3.  **Remove Default Date Filter (Incidents Route):** In `app/routes.py`, locate the `get_incidents` route (around line 236). Remove the identical hardcoded `1985` date filter logic.
4.  **Remove Default Date Filter (Export Route):** In `app/routes.py`, locate the `export_incidents_csv` route (around line 250). Remove the identical hardcoded `1985` date filter logic to ensure CSV exports match the UI.
5.  **Preserve User Date Filtering:** Ensure that if a user *does* explicitly set a "From Date" using the sidebar date picker, the `apply_incident_filters` function still correctly applies that user-defined constraint.

## 5. Non-Goals (Out of Scope)
*   Modifying the database schema or data ingestion scripts.
*   Making the Variant Comparison cards clickable (decision was made to remove them instead).
*   Adding new historical data sources; this only exposes data already residing in the database.

## 6. Design Considerations
*   With the Variant Comparison section removed, ensure the transition from the top stats grid directly into the Incident Feed (or AI Summary) looks visually cohesive without awkward spacing.

## 7. Technical Considerations
*   **Query Performance:** Removing the 1985 filter means queries for highly-incidenced aircraft (like early 737s) might return larger datasets by default. Ensure the existing `limit(50)` or pagination mechanisms (if any) are functioning correctly on the detail page to prevent slow render times.
*   **Date Parsing:** Verify that incidents with missing or malformed dates (which might be more common in pre-1985 historical records) do not crash the `order_by(Incident.date.desc())` sorting logic.

## 8. Success Metrics
*   Navigating to an older aircraft (e.g., Boeing 40) immediately displays its historical incidents in the feed without requiring manual filter adjustments.
*   The "Variant Comparison" header and cards are no longer visible on any aircraft detail page.
*   The CSV export for a historical aircraft correctly contains pre-1985 incidents by default.

## 9. Open Questions
*   None at this time.