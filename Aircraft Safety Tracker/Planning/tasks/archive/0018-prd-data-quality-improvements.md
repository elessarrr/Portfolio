# Product Requirements Document: Data Quality Improvements (Observations 26 Apr)

## 1. Introduction/Overview
This feature epic addresses four critical data quality and display issues identified in the April 26 observations:
1.  **Model Sorting Logic:** Inconsistent sorting where variant models appear before base models.
2.  **Capitalization Standardization:** Inconsistent casing (e.g., 'BOEING' vs 'Boeing').
3.  **Data Integrity in Series List:** Anomalous entries (e.g., standalone manufacturers or malformed models) appearing in the Series list.
4.  **Dead Link Detection and Removal:** Broken external links (NTSB reports) degrading the user experience.

The goal is to resolve these systematically to improve data reliability, UI consistency, and overall user trust. **Crucially, these four issues must be implemented and tested sequentially.** Each issue will be treated as a single variable change, followed by User Acceptance Testing (UAT), before moving to the next.

## 2. Goals
*   Ensure aircraft models are sorted logically (base models before variants).
*   Standardize all manufacturer and model names to Title Case across the database.
*   Prevent anomalous non-aircraft entries from appearing in the "Series" list.
*   Automatically identify and soft-delete/flag dead external links.
*   Maintain a safe deployment strategy by implementing and verifying one issue at a time.

## 3. User Stories
*   **As a user**, I want to see aircraft base models listed before their variants so that I can easily find and compare related aircraft.
*   **As a user**, I want to see consistent capitalization (Title Case) for all manufacturers and models so that the platform looks professional and trustworthy.
*   **As a user**, I want the "Series" list to only contain valid aircraft models so that I don't click on broken or malformed data.
*   **As a user**, I want to click on external incident report links and successfully reach the source document, rather than encountering 404s or "docket not released" errors.
*   **As an administrator**, I want a scheduled weekly job to automatically validate external links, and I want the ability to run this script manually when needed.

## 4. Functional Requirements
**Phase 1: Model Sorting Logic**
1.  The system must sort aircraft models alphabetically but prioritize base model names (e.g., "Boeing 747") over their variants (e.g., "Boeing 747-400").
2.  The sorting logic must be applied at the database query level or application layer before rendering lists on the UI.

**Phase 2: Capitalization Standardization**
3.  The system must include a one-time automated SQL/Python migration script to convert all existing manufacturer and model names (in `aircraft`, `aircraft_variant`, and `incident` tables) to Title Case.
4.  The system must ensure all new data ingested is converted to Title Case before being saved to the database.

**Phase 3: Data Integrity in Series List**
5.  The system must implement strict regex-based validation (e.g., `[Manufacturer] [Model Number]-[Variant]`) for aircraft model names during data ingestion.
6.  The system must reject or flag anomalous entries (like standalone manufacturers or malformed strings) before they reach the database.
7.  The system must include a one-time automated script to clean up existing historical anomalies in the database.

**Phase 4: Dead Link Detection and Removal**
8.  The system must include a `LinkValidator` script that performs HTTP HEAD/GET requests to validate URLs in the `IncidentSource` table.
9.  The script must handle timeouts (10s), rate limiting (delay of at least 1s between requests to the same domain), and content validation (e.g., checking for "docket not released").
10. The script must flag confirmed dead links in the database (e.g., soft deletion via `is_active = FALSE` or `status = 'dead'`) rather than hard deleting them.
11. The UI must filter out or visually indicate inactive/dead links.
12. The `LinkValidator` must be configured to run automatically as a weekly cron job.
13. The `LinkValidator` script must be saved in the `Planning/scripts` folder so it can be triggered manually via the CLI by an administrator.

## 5. Non-Goals (Out of Scope)
*   Building an Admin UI to manually review capitalization changes or dead links. (We are using automated scripts instead).
*   Implementing parallel fixes. (All fixes must be sequential and isolated for UAT).
*   Hard deletion of incident source records with dead links. (We will use soft deletion/flagging).
*   Fixing data issues outside of the four explicitly mentioned in the April 26 observations.

## 6. Design Considerations
*   **UI Updates:** The UI for the Series list and any dropdowns containing aircraft models will naturally reflect the new sorting and capitalization rules without requiring layout changes.
*   **Dead Links UI:** If a link is flagged as dead, the UI should ideally hide the link or display a disabled state with a tooltip (e.g., "Source link unavailable").

## 7. Technical Considerations
*   **Sorting Performance:** Using regex in SQL `ORDER BY` clauses (e.g., `regexp_replace`) can impact query performance. Consider evaluating performance on the staging database, and if too slow, consider a computed column or application-level sorting.
*   **LinkValidator Rate Limiting:** The LinkValidator must be robust enough to handle temporary network failures and strict NTSB server rate limits.
*   **Cron Job Environment:** Ensure the environment where the cron job runs has the necessary database credentials and Python dependencies.

## 8. Success Metrics
*   **Sorting:** 100% of aircraft lists display base models immediately preceding their variants.
*   **Capitalization:** 0 records in the database have inconsistent capitalization for manufacturer or model fields.
*   **Integrity:** 0 anomalous entries (e.g., 'BOEING' standalone) appear in the UI Series list.
*   **Dead Links:** Automated reports show active detection of dead links, and user bug reports regarding broken external links decrease to near zero.

## 9. Open Questions
*   For the sorting logic, should we add a `base_model` computed column to the `aircraft` table to improve sorting query performance, rather than computing it on the fly every time?
*   For the LinkValidator, should we send an email/Slack notification summary when the weekly cron job completes?
