## Relevant Files

- `app/models.py` - Database schema definitions for IncidentSource, SystemTag, AircraftVariant, and ReportAnalysis.
- `migrations/` - Database migration scripts.
- `scripts/scrape_boeing.py` - Existing scraper to be updated for variant parsing.
- `scripts/scrape_airbus.py` - Existing scraper to be updated for variant parsing.
- `scripts/scrape_faa.py` - New scraper for FAA database.
- `scripts/scrape_ntsb.py` - New scraper for NTSB database.
- `scripts/deduplicate.py` - Logic for merging and deduplicating incidents from multiple sources.
- `app/services/report_analyzer.py` - Service for AI report analysis.
- `app/routes.py` - API endpoints for report analysis and new filtering logic.
- `app/templates/index.html` - Main interface updates for the filter panel.
- `app/templates/aircraft.html` - Updates for variant comparison view.
- `app/static/js/main.js` - Frontend logic for filtering and dynamic UI updates.

### Notes

- Unit tests should typically be placed alongside the code files they are testing.
- Use `pytest` for running backend tests.

## Tasks

- [ ] 1.0 Database Schema & Core Models
  - [ ] 1.1 Define `IncidentSource` model in `app/models.py` (source_name, source_url, source_data, last_updated).
  - [ ] 1.2 Define `SystemTag` model in `app/models.py` (system_name, confidence, tagged_by).
  - [ ] 1.3 Define `AircraftVariant` model in `app/models.py` (variant_name, years_in_service, stats).
  - [ ] 1.4 Define `ReportAnalysis` model in `app/models.py` (root_cause, factors, summary, AI metadata).
  - [ ] 1.5 Generate and apply Alembic migration for the new tables.
  - [ ] 1.6 Add database indexes for performance (aircraft_id, date, system_tags, data_source).

- [ ] 2.0 Data Collection Pipeline (Scrapers)
  - [ ] 2.1 Update `scripts/scrape_boeing.py` and `scripts/scrape_airbus.py` to parse specific variants (e.g., 737-800 vs MAX 8).
  - [ ] 2.2 Enhance ASN scrapers to capture additional metadata (weather, phase of flight).
  - [ ] 2.3 Create `scripts/scrape_faa.py` to scrape the FAA Accident/Incident database.
  - [ ] 2.4 Create `scripts/scrape_ntsb.py` to scrape NTSB database and extract PDF report URLs.
  - [ ] 2.5 Implement robust error handling and rate limiting for all scrapers.

- [ ] 3.0 Data Processing & Deduplication
  - [ ] 3.1 Create `scripts/deduplicate.py` to implement exact matching logic (Date + Registration).
  - [ ] 3.2 Implement fuzzy matching logic (Date ±1 day + Model + Location) in `deduplicate.py`.
  - [ ] 3.3 Implement logic to flag discrepancies between sources (e.g., fatality counts).
  - [ ] 3.4 Create a unified incident view that aggregates data from linked sources.

- [ ] 4.0 AI Analysis Service
  - [ ] 4.1 Create `app/services/report_analyzer.py` with an adapter pattern for AI models (Gemini, Claude, etc.).
  - [ ] 4.2 Implement PDF text extraction (or handling) for report analysis.
  - [ ] 4.3 Create API endpoint `POST /api/analyze-report` in `app/routes.py`.
  - [ ] 4.4 Implement prompt engineering to extract root cause, contributing factors, and summaries.
  - [ ] 4.5 Add rate limiting and caching for AI analysis requests to manage costs/quotas.

- [ ] 5.0 Frontend & UI Overhaul
  - [ ] 5.1 Update `app/templates/base.html` and `index.html` to include a persistent, collapsible sidebar filter panel.
  - [ ] 5.2 Implement multi-select filters for System Tags, Variants, and Data Sources in `app/static/js/main.js`.
  - [ ] 5.3 Update the incident list component to display Source Badges ([ASN], [FAA], [NTSB]) and System Tags.
  - [ ] 5.4 Create a Variant Comparison view in `app/templates/aircraft.html` (side-by-side stats).
  - [ ] 5.5 Implement the "AI Analysis" card component with "Experimental" warning and disclaimer.
  - [ ] 5.6 Implement CSV export functionality for filtered results.
