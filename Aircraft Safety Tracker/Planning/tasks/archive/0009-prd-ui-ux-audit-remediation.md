# 0009-prd-ui-ux-audit-remediation

## 1. Introduction/Overview
The Aircraft Safety Tracker application recently underwent a comprehensive UI/UX audit on April 18, 2026. While the core data model and navigation are sound, several critical and high-priority issues were identified that undermine user trust, professional polish, and overall usability. This PRD outlines the remediation plan to address these specific issues, focusing on broken assets, non-functional AI features, layout inconsistencies, missing feedback states, and data presentation. The goal is to elevate the application to a "launch-ready" state within a 2-3 day focused development sprint.

## 2. Goals
*   **Restore User Trust:** Eliminate all visual indicators of a "broken" application (specifically broken images and hanging loading states).
*   **Improve Data Readability:** Ensure long text blocks and empty data states are handled gracefully.
*   **Provide User Feedback:** Implement loading and error states across the application so users are never left guessing about system status.
*   **Enhance Visual Polish:** Standardize chart layouts and ensure basic responsive behavior.

## 3. User Stories
*   **As a user**, I want to view incident cards without seeing broken image icons, so that the application feels professional and trustworthy.
*   **As a user**, I want the AI summary feature to either load successfully or tell me it failed, so I am not left waiting indefinitely.
*   **As a user**, I want to see only the filters that are relevant and have data for a specific aircraft, so I don't waste time trying to filter by non-existent tags.
*   **As a user**, I want to easily scan through incident lists without extremely long descriptions breaking the layout, while still having the option to read the full text if I choose.
*   **As a user**, I want visual confirmation when I perform an action (like searching or filtering) so I know the system is processing my request.
*   **As a user**, I want to be informed if an action fails (e.g., via a toast notification or inline message) so I know I need to try again.

## 4. Functional Requirements

1.  **Remove Broken Image Assets:** Completely remove the image elements/icons from all incident cards on the Incidents page. Do not attempt to load or display airline logos or incident photos.
2.  **Fix AI Summary Generation:** Diagnose and resolve the backend API connection issue (Gemini/DeepSeek) that is causing the AI summary on Aircraft Detail pages to hang indefinitely. The system must successfully return and display the generated summary.
3.  **Hide Empty Filter Sections:** On the Aircraft detail page sidebar, dynamically hide entire filter sections (e.g., "System Tags", "Variants", "Source Metadata") if there is no underlying data available for the currently viewed aircraft. Do not display "No [X] available" messages.
4.  **Truncate Incident Descriptions:** Implement CSS/JS to truncate long incident descriptions on the Incidents page to a maximum of 3-4 lines.
5.  **Implement "Read More" Expansion:** For truncated incident descriptions, provide a clickable "Read more" link inline that expands the text box to show the full description without navigating away from the page.
6.  **Standardize Chart Layout:** Update CSS for the dashboard section on the Incidents page to ensure the "Incidents by Manufacturer" chart and the "Severity Breakdown" chart maintain consistent widths and responsive behavior (e.g., using CSS Grid).
7.  **Implement Global Loading States:** 
    *   Display a spinner or skeleton loader during search query execution.
    *   Display a loading indicator (e.g., on the button itself) when the "Apply Filters" action is processing.
8.  **Implement Global Error Handling:**
    *   Implement a system for displaying error messages (e.g., toast notifications or inline alerts) if an API call (search, filter, summary generation) fails.
9.  **Handle "Years in Service" Data Issue:** If the "Years in Service" data point for an aircraft is null, missing, or evaluates to "Unknown", hide the field entirely from the Aircraft detail page rather than displaying the word "Unknown".

## 5. Non-Goals (Out of Scope)
*   Adding new major features (e.g., user accounts, email alerts).
*   Implementing a new safety scoring system (A-F grades, 1-10 scores).
*   Building dedicated, standalone incident detail pages (continue relying on external ASN links for now).
*   Complete mobile-first redesign (basic responsiveness fixes are in scope, but not a full overhaul).
*   Resolving the Tailwind CDN warning or implementing a full npm build process at this time.
*   Implementing comprehensive analytics tracking.

## 6. Design Considerations
*   **Incident Cards:** With images removed, ensure the text layout shifts appropriately to utilize the reclaimed space effectively.
*   **"Read More":** The toggle should look like a standard text link (e.g., blue text, pointer cursor) and smoothly transition the container height.
*   **Charts:** Ensure the CSS Grid implementation for the dashboard charts gracefully collapses to a single column on smaller viewports.

## 7. Technical Considerations
*   **AI Summary:** The root cause of the hanging summary is likely an unhandled exception or timeout in `app/services/deepseek.py` or `app/services/gemini.py` not being properly communicated back to the polling UI (`summary_card_polling.html`). This needs backend debugging.
*   **HTMX:** Leverage existing HTMX patterns for loading states (e.g., `htmx-indicator` classes) and error handling where applicable.
*   **Jinja Templates:** The logic for hiding empty filters and the "Years in Service" field should be handled primarily via Jinja `{% if %}` conditional statements in the templates.

## 8. Success Metrics
*   0 broken image links visible across the application.
*   100% success rate (or clear error message display) for AI summary generation requests.
*   No empty filter sections visible on any Aircraft detail page.
*   All long incident descriptions are cleanly truncated with a functional expansion toggle.

## 9. Open Questions
*   Are there any specific error monitoring tools (like Sentry) we should integrate the new error handling with, or is console logging sufficient for this pass?
