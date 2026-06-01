# 0010-prd-ui-simplification-removals

## 1. Introduction/Overview
The Aircraft Safety Tracker application currently displays a 'Years in Service' card and an 'AI Analysis' card on the aircraft detail page. Based on user feedback and an April 18th enhancements list, these cards are either non-functional, non-critical, or experimental. This feature request focuses on simplifying the UI by removing these specific cards from the front-end view while preserving their underlying backend logic and data structures for potential future use.

## 2. Goals
*   Simplify the user interface on the aircraft detail page.
*   Remove non-functional and experimental components ('Years in Service' and 'AI Analysis') from the user's view.
*   Ensure the remaining UI components re-adjust smoothly to fill the newly available space.
*   Preserve the backend data, database columns, and API endpoints related to these features for future iterations.

## 3. User Stories
*   **As a user**, I want a cleaner, less cluttered aircraft detail page so that I can focus on the most important safety statistics and incident history.
*   **As a user**, I don't want to see broken or experimental features (like 'Years in Service' or 'AI Analysis') that distract from the core data.

## 4. Functional Requirements

1.  **Remove 'Years in Service' UI:** Delete the HTML/Jinja template code that renders the 'Years in Service' card (typically found in `app/templates/components/stats_grid.html` or `aircraft.html`). 
2.  **Preserve 'Years in Service' Data:** Do not alter the `Aircraft` database model's `years_in_service` column or any backend logic that populates it.
3.  **Remove 'AI Analysis' UI:** Delete the HTML/Jinja template code and any associated front-end JavaScript that renders the 'AI Analysis' (Experimental) card and its report submission form.
4.  **Preserve 'AI Analysis' Backend:** Do not alter or delete the `/api/analyze-report` endpoint, the `ReportAnalyzerService`, or any of the AI adapter code (`gemini.py`, `deepseek.py`).
5.  **Dynamic Layout Adjustment:** Update the CSS Grid or Flexbox layout classes on the parent container (e.g., the stats grid) to ensure the remaining cards dynamically expand or shift to fill the empty space left by the removed cards smoothly.

## 5. Non-Goals (Out of Scope)
*   Deleting database columns or running database migrations.
*   Removing backend Python services or API routes.
*   Adding new UI components or features.

## 6. Design Considerations
*   **Layout Re-adjustment:** When removing elements from a CSS Grid, ensure `grid-template-columns` is set to automatically fill the space (e.g., using `auto-fit` or adjusting column spans) so the layout doesn't look lopsided.
*   **Visual Balance:** Verify that the primary safety summary card and the incident counts card look balanced and well-proportioned after the removals.

## 7. Technical Considerations
*   **HTMX / JavaScript:** Ensure that removing the 'AI Analysis' card doesn't leave behind broken JavaScript event listeners or orphaned HTMX attributes that cause console errors.
*   **Template Cleanup:** Be careful to remove the entire component blocks in Jinja, including any wrapper `div` elements specific to those cards.

## 8. Success Metrics
*   The 'Years in Service' card is no longer visible anywhere in the application.
*   The 'AI Analysis' card and its input form are no longer visible.
*   The remaining UI components successfully reorganize to use the available screen space without leaving awkward gaps.
*   Backend tests and API endpoints for the removed features still pass/function independently.

## 9. Open Questions
*   None at this time.
