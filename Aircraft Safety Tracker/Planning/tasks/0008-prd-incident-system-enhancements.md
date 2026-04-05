# Product Requirements Document (PRD): Incident System Enhancements

## 1. Introduction/Overview
The aviation incident tracking system currently struggles with data fragmentation, incomplete aircraft model coverage, and limited incident card navigation. This project aims to resolve these critical issues by integrating data from multiple sources (ASN, NTSB, and FAA), automatically identifying and backfilling missing aircraft models, and improving user navigation from incident lists to specific aircraft pages. The goal is to create a more unified, accurate, and user-friendly experience for researching aviation safety.

## 2. Goals
*   **Establish a Single Source of Truth:** Successfully merge overlapping incidents from ASN, NTSB, and FAA into unified records while retaining links to original sources.
*   **Achieve 100% Model Coverage:** Programmatically discover and automatically create missing Boeing and Airbus aircraft models based on historical incident data.
*   **Improve Navigation Flow:** Allow users to easily drill down from a global incident card directly into an aircraft's dedicated safety profile in a new tab.
*   **Enhance Data Quality:** Automatically clean up duplicated manufacturer names (e.g., "Boeing Boeing 717" to "Boeing 717") to ensure a professional UI.

## 3. User Stories
*   **As an aviation researcher**, I want to see all available official sources (NTSB, FAA, ASN) for a single incident in one place, so that I can easily verify the facts and read the original reports.
*   **As a data analyst**, I want the system to warn me if different sources report conflicting data for the same incident (e.g., different fatality counts), so that I am aware of discrepancies.
*   **As a user exploring safety records**, I want to click on the aircraft badge on any incident card to open that specific aircraft's full safety profile in a new tab, so that I can investigate its overall history without losing my place in the main list.
*   **As a system administrator**, I want the platform to automatically detect and create aircraft models that exist in the incident data but are missing from the database, so that no incidents are orphaned or hidden.

## 4. Functional Requirements

### 4.1. Multi-Source Incident Integration
1.  **Unified Data Architecture:** The system must merge records from ASN, NTSB, and FAA that share the same date, location, and aircraft registration into a single primary `Incident` record.
2.  **Cross-Referencing Display:** The incident card must display all available source references (badges) for the unified incident.
3.  **Direct Source Links:** Where available, the source badges must act as hyperlinks directing the user to the official NTSB or FAA database record.
4.  **Discrepancy Warning Flag:** If the merged sources contain conflicting data for critical fields (e.g., different fatality counts between NTSB and ASN), the UI must display a clear "Data Discrepancy" warning flag or tooltip on the incident card.

### 4.2. Complete Aircraft Model Coverage
5.  **Reverse-Engineering Missing Models:** During the data ingestion process, if an incident is tied to an aircraft model (Boeing or Airbus) that does not exist in the `Aircraft` database table, the system must automatically create the new aircraft profile.
6.  **Auto-Publishing:** Newly discovered aircraft models must be published and made visible to users immediately.
7.  **Automated Backlog Verification:** When a new model is auto-created, the system must trigger a background check (or log a backlog task) to scan all raw ingested data and confirm that other observations/incidents exist for this newly created model.
8.  **Data Clean-up (Duplicate Stripping):** During data validation and ingestion, the system must automatically strip consecutively duplicated *alphabetic* words in manufacturer or model names (e.g., "Boeing Boeing 717" becomes "Boeing 717"). It must *not* strip duplicated numbers (e.g., "700-700" remains "700-700").
9.  **Dropdown Synchronization:** The homepage dropdown list of aircraft models must dynamically update to include any newly discovered and auto-created models.

### 4.3. Enhanced Incident Card Navigation
10. **Clickable Aircraft Badge:** The aircraft model badge (located in the top-right corner of the incident cards on the global incidents page) must be a clickable hyperlink.
11. **New Tab Navigation:** Clicking the aircraft badge must navigate the user to that specific aircraft's dedicated safety page (`/aircraft/<id>`) in a **new browser tab** (`target="_blank"`).

## 5. Non-Goals (Out of Scope)
*   Creating a manual admin UI for reviewing and approving newly discovered aircraft models (they will be auto-published instead).
*   Integrating additional data sources beyond ASN, NTSB, and FAA for this specific phase.
*   Applying the duplicate word stripping logic to numerical data or other fields outside of the Manufacturer/Model name.

## 6. Design Considerations
*   **Discrepancy Flag UI:** The "Data Discrepancy" warning should be a small, non-intrusive icon (e.g., a yellow triangle with an exclamation mark) that explains the conflict when hovered over.
*   **Clickable Badges:** The aircraft badge on the incident card should have clear interactive hover states (e.g., underline, slight color change, pointer cursor) so users know it is clickable.

## 7. Technical Considerations
*   **Deduplication Logic:** The existing `app/ingestion/dedupe.py` will need to be updated to evaluate data discrepancies across linked `IncidentSource` records and set a flag on the parent `Incident` model if conflicts are found.
*   **Regex for Duplicate Stripping:** Use a case-insensitive regular expression to find and replace consecutive duplicate alphabetic words (e.g., `\b([A-Za-z]+)\s+\1\b`) in the parser/importer layer before saving to the database.
*   **Background Tasks:** The "Automated Backlog Verification" for new models may require a lightweight background task queue (like the existing threading implementation used for AI summaries) to avoid slowing down the main ingestion pipeline.

## 8. Success Metrics
*   **Zero Orphaned Incidents:** 100% of ingested NTSB/FAA incidents are successfully mapped to a valid aircraft model.
*   **Data Cleanliness:** 0 occurrences of "Boeing Boeing" or "Airbus Airbus" in the production database.
*   **Navigation Engagement:** At least 15% of users clicking on an incident card badge to view the dedicated aircraft page (measured via standard web analytics).

## 9. Open Questions
*   How should the automated backlog verification report its findings? Should it email an admin, or just write to a specific log file (`data/logs/model_verification.log`)?
*   For the discrepancy warning flag, which specific fields should trigger the warning? (Currently assuming just `fatalities`, but should it include `date` or `location` mismatches?)