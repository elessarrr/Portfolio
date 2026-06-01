# 0012-prd-data-visibility-and-attribution

## 1. Introduction/Overview
This Product Requirements Document (PRD) addresses key enhancements related to data visibility, AI summary generation, and data attribution within the Aircraft Safety Tracker application. The goal is to improve user experience by conditionally displaying AI summaries, ensuring all ingested data sources are effectively utilized and presented, and providing clear, unified data attribution in the footer.

## 2. Goals
*   **Optimize AI Summary Display:** Prevent unnecessary AI summary generation and display for aircraft with no incidents.
*   **Enhance Data Source Utilization:** Ensure all available data sources (NTSB, FAA_AIDS, FAA_SDR, ASN) are leveraged and prioritized in incident displays.
*   **Improve Data Attribution:** Provide a clear, consistent, and informative data attribution section in the website footer, including freshness indicators.

## 3. User Stories
*   **As a user**, I don't want to see an AI summary attempting to generate for an aircraft with no incidents, as it's confusing and wastes my time.
*   **As a user**, I want to see the most comprehensive incident data available, prioritized from official sources, so I can trust the information presented.
*   **As a user**, I want to easily understand where the application's data comes from and how fresh it is, so I can assess its reliability.

## 4. Functional Requirements

1.  **Conditional AI Safety Summary Display:**
    *   On the aircraft detail page, if `aircraft.total_incidents` is 0, the entire "AI Safety Summary" card (including the header, loading message, and disclaimer) must be hidden.
    *   The backend should not initiate any AI summary generation process if `aircraft.total_incidents` is 0.

2.  **Prioritized Display of Incident Data Sources:**
    *   The application must prioritize incident data display based on the following hierarchy: NTSB > FAA_AIDS > FAA_SDR > ASN.
    *   When displaying incidents, if an incident exists in multiple sources, the data from the highest priority available source should be used.
    *   The UI should clearly indicate the source of each displayed incident (e.g., a small badge or text next to the incident entry).
    *   A comprehensive codebase analysis must be conducted to identify and resolve any technical implementation gaps, data pipeline configurations, or UI/UX barriers preventing these sources from being effectively showcased.

3.  **Redesigned Footer for Unified Data Attribution:**
    *   The website footer must be redesigned to include a consolidated data attribution section.
    *   This section should prominently display the text: "Data sourced from below sources. Not affiliated with any manufacturer."
    *   All data sources (ASN, FAA_AIDS, FAA_SDR, NTSB) must be clearly listed.
    *   For each listed data source, a "Data Freshness" indicator must be added, displaying the month and year of the last update (e.g., "ASN: Apr 2026", "NTSB: Mar 2026").

## 5. Non-Goals (Out of Scope)
*   Adding new data sources beyond the existing ASN, FAA_AIDS, FAA_SDR, and NTSB.
*   Implementing user-selectable filters for data sources at this stage.
*   Real-time data freshness updates (manual updates of month/year are sufficient for now).

## 6. Design Considerations
*   **AI Summary:** Ensure the removal of the AI Summary card for zero-incident aircraft does not create awkward empty space or layout issues on the aircraft detail page.
*   **Data Source Indicator:** The UI indicator for incident sources should be subtle but clear, possibly a small icon or text label.
*   **Footer:** The redesigned footer should be visually clean and integrate seamlessly with the existing Tailwind CSS styling.

## 7. Technical Considerations
*   **AI Summary:** The conditional display logic for the AI Summary card should be implemented in the Jinja template (`aircraft.html` or `summary_card_polling.html`) and potentially in the `aircraft_details` route in `app/routes.py` to prevent unnecessary job creation.
*   **Data Source Prioritization:** This will likely involve modifications to the `apply_incident_filters` function in `app/routes.py` and potentially the `Incident` model queries to ensure the correct source is selected and displayed. The `IncidentSource` model will be crucial here.
*   **Footer Freshness:** This will require a mechanism to store and retrieve the last update month/year for each data source, possibly in a configuration file or a simple database table. The footer template (`base.html` or a dedicated footer component) will need to be updated.

## 8. Success Metrics
*   The AI Safety Summary card is never displayed for aircraft with `total_incidents` equal to 0.
*   Incident listings consistently display data from the highest priority source available (NTSB > FAA_AIDS > FAA_SDR > ASN).
*   The footer clearly shows the unified attribution text and month/year freshness for all four data sources.

## 9. Open Questions
*   None at this time.