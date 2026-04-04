# Product Requirements Document: Comprehensive Incidents Database & Boeing Data Resolution

## 1. Introduction/Overview
Currently, our Boeing incident data is severely incomplete due to a truncated raw data file that ended at the Boeing 707, omitting major models like the 737, 747, and 777. Combined with our rule to filter out incidents prior to 1985, almost no Boeing incidents are currently visible in the system. This project will resolve the missing aircraft data by leveraging both Aviation Safety Network (ASN) and official US databases (NTSB/FAA), relying on our deduplication pipeline to merge records. Additionally, we will design and build a dedicated "Incidents Database" page providing users with a master view of all aviation incidents on file, equipped with advanced filtering, infinite scroll, and interactive data visualizations.

## 2. Goals
*   **Resolve Missing Data:** Backfill all missing Boeing commercial models (717, 727, 737, 747, 757, 767, 777, 787) ensuring complete incident histories post-1985.
*   **Establish Single Source of Truth:** Combine ASN's global coverage with NTSB/FAA's detailed US coverage, using automated deduplication.
*   **Comprehensive Search & Discovery:** Build a dedicated incidents page allowing users to explore the entire database holistically rather than navigating model by model.
*   **Data Visualization:** Implement interactive charts to expose safety trends, severities, and geographical distributions at a glance.

## 3. User Stories
*   **As an aviation enthusiast or researcher,** I want to browse a single page containing all recorded aviation incidents, so that I can explore historical safety records without knowing the specific aircraft model beforehand.
*   **As an investigator,** I want to filter the global incidents database by year range and aircraft model, so that I can isolate specific eras and families of aircraft for analysis.
*   **As a data analyst,** I want to see visual trends (like fatal vs. non-fatal incidents over time), so that I can easily spot improvements or regressions in aviation safety.
*   **As an end user,** I want the page to load quickly and use infinite scroll, so that I can seamlessly browse thousands of records without clicking through pages.

## 4. Functional Requirements
1.  **Data Ingestion & Resolution:**
    *   The system must ingest complete historical data for all Boeing and Airbus models from both ASN (via scraping) and NTSB/FAA (via existing bulk importers).
    *   The system must deduplicate records where incidents overlap between sources, merging facts into a canonical record.
2.  **Incidents Database Page UI:**
    *   The system must provide a dedicated route (e.g., `/incidents`) for the comprehensive database.
    *   The page must implement infinite scroll, loading incidents dynamically as the user scrolls down the page.
    *   The default view must present a filtered subset of data or a dashboard of charts to prevent loading all 1,500+ incidents simultaneously.
3.  **Filtering & Search:**
    *   The page must include persistent filter controls for: Year Range (e.g., 1985 to 2025), Aircraft Manufacturer/Model, Incident Severity (Fatal/Non-fatal), and Geographical Location.
4.  **Data Visualizations (Charts & Graphs):**
    *   The page must render interactive charts displaying: Timeline Trends (Incidents per year by model), Severity Breakdown (Fatal vs. Non-fatal over time), System Failures (Incidents by root cause/tag), and a Geographic Map of incident locations.
    *   Charts must dynamically update based on the active filters.

## 5. Non-Goals (Out of Scope)
*   Adding new aircraft manufacturers beyond Boeing and Airbus (e.g., Embraer, Bombardier).
*   Building a completely new deduplication engine (we will use the existing `dedupe.py` pipeline).
*   Live/Real-time streaming of new incidents (updates will remain batch/scheduled).

## 6. Design Considerations
*   **Infinite Scroll Performance:** Ensure the HTMX or JavaScript infinite scroll implementation efficiently manages DOM nodes to prevent browser memory bloat.
*   **Chart Library:** Utilize a lightweight, responsive charting library (like Chart.js or Recharts) that integrates cleanly with Flask and HTMX.
*   **Responsive Layout:** The filter sidebar should collapse on mobile devices, stacking the charts above the infinite-scroll list.

## 7. Technical Considerations
*   **Data Migration Strategy:** We must generate a complete `boeing_incidents.json` to replace the truncated file, run the `import_data.py` script, and subsequently trigger the NTSB/FAA bulk importers to backfill and deduplicate.
*   **Database Query Optimization:** The `/incidents` endpoint powering the infinite scroll must use efficient SQL pagination (`LIMIT` / `OFFSET`) and indexed columns (Date, Aircraft ID) to maintain sub-100ms response times.
*   **API Endpoint:** A new internal endpoint (e.g., `GET /api/incidents/page/<n>`) will be required to serve the HTML fragments for the infinite scroll.

## 8. Success Metrics
*   **Data Integrity:** 100% of major Boeing commercial models (737, 747, 777, etc.) are present in the database with post-1985 incident histories.
*   **Performance Benchmark:** The incidents database page and its charts must render the initial view in under 1.5 seconds.
*   **User Experience:** Infinite scroll successfully fetches and appends the next batch of incidents in under 500ms.

## 9. Open Questions
*   Should the Geographic Map visualization plot exact lat/long coordinates (requiring geocoding), or group incidents by Country/Region based on text strings?
*   When deduplicating ASN and NTSB data, if casualty counts conflict, which source is treated as the ultimate source of truth? (Currently NTSB is prioritized, need to confirm this remains true).