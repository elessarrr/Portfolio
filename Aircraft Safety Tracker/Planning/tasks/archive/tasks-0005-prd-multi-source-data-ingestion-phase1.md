## Relevant Files

- `Planning/0005-prd-multi-source-data-ingestion-phase1.md` - Source PRD defining Phase 1 ingestion requirements.
- `app/models.py` - Contains `Incident`, `IncidentSource`, `SystemTag`; will need schema extensions and new models.
- `migrations/` - Alembic migrations for new tables/columns/indexes required by multi-source ingestion.
- `app/routes.py` - Implements incident filtering and summary generation; will need source filtering and (later) source-aware detail rendering.
- `app/templates/components/incident_list.html` - Incident list UI; will need source badges and linked-source display.
- `app/templates/aircraft.html` - Aircraft detail page; will need improved “Data Sources” UX and “last updated” visibility.
- `app/templates/base.html` - Footer; will need per-source “last updated” timestamps.
- `scripts/import_data.py` - Current ASN-only importer; can be refactored or wrapped into the new importer framework.
- `scripts/deduplicate.py` - Current file-based dedupe prototype; useful reference for matching heuristics to implement in DB.
- `scripts/scrape_ntsb.py` - Current NTSB web scrape prototype; may be replaced by API/bulk importer.
- `scripts/scrape_faa.py` - Current FAA web scrape prototype; may be replaced by AIDS/SDR importers.
- `scripts/asn_sync.py` - Existing sync-state patterns (lock + timestamps) that can inform per-source import state.
- `tests/test_routes.py` - Route tests; will need coverage for source filtering and source badges.
- `tests/test_models.py` - Model tests; will need coverage for new tables and constraints.
- `migrations/versions/8d2a1c4f0b17_add_import_log_table.py` - Adds `import_log` table and merges Alembic heads.
- `migrations/versions/0f6d7d9c3f2a_add_jasc_mapping_table.py` - Adds `jasc_mapping` table for JASC-to-system mappings.
- `migrations/versions/3a91c2c7d1e4_extend_incident_source_fields.py` - Extends `incident_source` with record IDs and confidence.
- `migrations/versions/6f1f0b2a9b77_add_indexes_and_constraints_for_sources.py` - Adds indexes/constraints for source filtering and dedupe lookups.
- `app/ingestion/importers/base.py` - Base importer abstraction used by all source importers.
- `tests/test_importer_base.py` - Unit tests for importer base behavior and ImportLog integration.
- `migrations/versions/1b2e0c9f7a6d_add_import_state_table.py` - Adds `import_state` table for per-source state tracking.
- `app/ingestion/cli.py` - CLI entrypoints for `flask import-data ...` commands.
- `tests/test_import_cli.py` - CLI tests validating the `import-data` group exists and runs.
- `app/ingestion/clients/ntsb.py` - NTSB HTTP API client with 429 backoff and batching helpers.
- `tests/test_ntsb_client.py` - Unit tests for NTSB API client retry and batching logic.
- `app/ingestion/bulk/ntsb_bulk.py` - NTSB bulk download + unzip + delimited parsing utilities.
- `tests/test_ntsb_bulk.py` - Unit tests for NTSB bulk zip extraction and parsing.
- `app/ingestion/bulk/faa_aids_bulk.py` - FAA AIDS bulk download + unzip + delimited parsing utilities.
- `tests/test_faa_aids_bulk.py` - Unit tests for FAA AIDS downloader/parser and URL building.
- `app/ingestion/importers/faa_aids_importer.py` - FAA AIDS importer mapping records into `Incident` + `IncidentSource`.
- `tests/test_faa_aids_importer.py` - Tests for FAA AIDS importer normalization and upsert behavior.
- `app/ingestion/bulk/faa_sdr_bulk.py` - FAA SDR annual CSV downloader/parser utilities.
- `tests/test_faa_sdr_bulk.py` - Unit tests for FAA SDR downloader/parser.
- `app/ingestion/normalization/jasc.py` - JASC code normalization/validation helpers.
- `tests/test_jasc_normalization.py` - Tests for JASC code parsing/validation.
- `app/ingestion/system_tagging.py` - Applies JASC mappings to create `SystemTag` entries.
- `tests/test_system_tagging.py` - Tests for JASC-based system tagging and fallback behavior.
- `app/ingestion/seed/jasc_seed.py` - Default JASC-to-system seed mappings.
- `migrations/versions/2a6d4c0b9e12_add_unmapped_jasc_table.py` - Adds `unmapped_jasc` table to track unmapped codes.
- `app/ingestion/dedupe.py` - Deduplication matching heuristics and decision persistence.
- `migrations/versions/6c3d9a1e2f0b_add_dedupe_decision_table.py` - Adds `dedupe_decision` table to persist link/merge decisions.
- `tests/test_dedupe.py` - Tests for dedupe matching rules and persisted decisions.
- `app/ingestion/canonical.py` - Canonical field selection rules and source attachment helper.
- `app/ingestion/importers/ntsb_importer.py` - NTSB importer mapping records into `Incident` + `IncidentSource`.
- `tests/test_ntsb_importer.py` - Tests for NTSB importer normalization and upsert behavior.
- `migrations/versions/4b7c1d2e9a31_add_report_url_to_incident_source.py` - Adds `incident_source.report_url` for PDF report links.

### Notes

- API keys must be provided via environment variables / `.env` and never committed.

## Tasks

- [ ] 1.0 Extend database schema for multi-source ingestion
  > **Context:** Transitions the database from a single-source architecture (ASN) to a robust multi-source model.
  > **Why/Value:** Essential for storing overlapping reports of the same incident without data loss, enabling a unified, high-confidence safety tracker.
  - [x] 1.1 Add `ImportLog` model/table for per-run tracking and metrics.
    > **Context:** Creates an audit trail for data ingestion runs. Allows us to monitor pipeline health, debug failures, and track processing metrics.
  - [x] 1.2 Add `JASCMapping` model/table for mapping JASC codes to `SystemTag`.
    > **Context:** The FAA uses JASC (Joint Aircraft System/Component) codes. This lookup table maps those opaque codes to human-readable `SystemTag`s for consistent UI filtering.
  - [x] 1.3 Extend `IncidentSource` fields to match PRD (record ID + confidence + timestamps).
    > **Context:** Adds metadata to track where data came from and how reliable it is. Crucial for the deduplication engine to weigh which source's data is more authoritative.
  - [x] 1.4 Add indexes/constraints needed for source filtering and dedupe lookups.
    > **Context:** Optimizes database read performance for source-based filtering and speeds up the deduplication matching queries (e.g., fast lookups on exact dates and locations).
  - [x] 1.5 Add migration(s) for schema updates and verify both SQLite + Postgres paths.
    > **Context:** Safely applies schema changes across environments. Testing on both SQLite (local dev) and Postgres (production) ensures no deployment surprises.

- [ ] 2.0 Create importer framework + CLI entrypoints + per-source import state
  > **Context:** Establishes a scalable, standardized ETL (Extract, Transform, Load) pipeline.
  > **Why/Value:** Replaces ad-hoc scripts with a unified architecture, making it easy to monitor current imports and seamlessly add new sources in the future.
  - [x] 2.1 Create `DataSourceImporter` base class with standardized hooks (fetch, parse, validate, upsert).
    > **Context:** Enforces a consistent interface for all importers. Reduces code duplication and centralizes error handling and logging.
  - [x] 2.2 Implement per-source state tracking (last successful import timestamp + counts + errors).
    > **Context:** Enables incremental imports. By knowing the last successful sync, we only fetch new or updated records, drastically reducing API load and import time.
  - [x] 2.3 Add `flask import-data` CLI group with per-source commands and date/year parameters.
    > **Context:** Provides a developer-friendly and cron-friendly interface to trigger specific imports (e.g., `flask import-data ntsb --year 2023`).
  - [x] 2.4 Implement structured import logging to `data/logs/import_YYYYMMDD_HHMMSS.log`.
    > **Context:** Writes detailed, parseable logs to disk. Essential for post-mortem debugging if an import job fails silently or corrupts data.
  - [x] 2.5 Ensure failures in one source do not block remaining sources.
    > **Context:** Implements fault isolation. If the FAA API goes down, NTSB data should still ingest successfully. Increases overall system resilience.

- [ ] 3.0 Implement NTSB importer (API + bulk download parsing)
  > **Context:** Integrates the primary US investigative body's data.
  > **Why/Value:** NTSB provides the most authoritative probable cause and findings, acting as our highest-confidence data source for North American incidents.
  - [x] 3.1 Implement NTSB API client with batching and backoff on 429.
    > **Context:** Handles network unreliability. Batching and exponential backoff prevent us from being rate-limited or blocked by the NTSB servers.
  - [x] 3.2 Implement bulk download fetch + unzip + parsing for tab-delimited files.
    > **Context:** The NTSB provides historical data in bulk zips. This is much faster for the initial database seed than making millions of individual API calls.
  - [x] 3.3 Normalize NTSB fields into `Incident` + `IncidentSource` (probable cause, findings, injuries, etc.).
    > **Context:** Translates NTSB's specific taxonomy into our universal `Incident` schema so the UI can display it agnostically.
  - [x] 3.4 Store NTSB PDF report URL and key identifiers in `IncidentSource`.
    > **Context:** Gives users direct access to the official primary source document, building trust in our platform's data.
  - [x] 3.5 Add validation for required fields and date range (1985–2025).
    > **Context:** Protects the database from bad data. Enforcing date ranges prevents garbage data (e.g., 1899 defaults) from corrupting the timeline.

- [ ] 4.0 Implement FAA AIDS + FAA SDR importers (including JASC mapping to SystemTag)
  > **Context:** Integrates FAA operational and maintenance data.
  > **Why/Value:** AIDS covers general aviation incidents, while SDRs (Service Difficulty Reports) give early warnings on mechanical failures, broadening our safety coverage.
  - [x] 4.1 Implement FAA AIDS downloader/parser (tab-delimited zip) with year/month support.
    > **Context:** Automates fetching the periodic zip files from the FAA, replacing manual downloads and ensuring data stays fresh.
  - [x] 4.2 Map FAA AIDS fields into `Incident` + `IncidentSource` (narrative, findings, phase, etc.).
    > **Context:** Aligns FAA's specific data fields to our global schema, ensuring consistency across different data providers.
  - [x] 4.3 Implement FAA SDR annual CSV downloader/parser with year parameter.
    > **Context:** Handles the specific format of SDRs, which are critical for tracking component-level reliability (e.g., specific engine or landing gear issues).
  - [x] 4.4 Parse JASC code fields and validate against expected format.
    > **Context:** Validates JASC codes to ensure they match the standard 4-digit format, rejecting or flagging malformed data before it enters the database.
  - [x] 4.5 Apply `JASCMapping` to create `SystemTag` associations (and fallback “Unknown System”).
    > **Context:** Automatically tags incidents with systems like "Landing Gear" or "Hydraulics" based on the JASC code, enabling powerful analytical filters.
  - [x] 4.6 Seed initial JASC-to-system mappings and add admin workflow for unmapped codes.
    > **Context:** Bootstraps the system with known codes so it's useful on day one, and provides a fallback to catch and map new/unknown codes as they appear.

- [ ] 5.0 Implement deduplication/linking and UI source attribution (badges, filters, freshness)
  > **Context:** The core intelligence of the multi-source system and the user-facing representation of that data.
  > **Why/Value:** Solves the "split-brain" problem (where one real-world crash appears as multiple separate incidents) and provides visual transparency to the user.
  - [x] 5.1 Implement dedupe matching rules (exact + fuzzy) and persist merge/link decisions.
    > **Context:** Uses heuristics (date, location, aircraft tail number) to detect when records describe the same event. Fuzzy matching handles slight typos between agencies.
  - [x] 5.2 Choose canonical record rules (NTSB preferred) and attach other sources via `IncidentSource`.
    > **Context:** Establishes a hierarchy of truth. NTSB is preferred for fatalities/causes, while FAA might be preferred for exact flight hours.
  - [x] 5.3 Add “Data Sources” filter behavior end-to-end (query + UI checkboxes).
    > **Context:** Exposes the multi-source capability to the user, allowing them to filter the dashboard to only show, e.g., NTSB-verified incidents.
  - [x] 5.4 Render source badges per incident row and show “Also reported by …” links.
    > **Context:** Provides visual transparency. Users can instantly see which agencies corroborated an incident, increasing confidence in the data.
  - [x] 5.5 Display per-source “Last updated” timestamps in footer.
    > **Context:** Builds user trust by showing exactly how fresh the data is for each source pipeline.
  - [x] 5.6 Add tests for importer validation, source linking, and source filtering.
    > **Context:** Ensures the complex deduplication logic and critical ETL pipelines don't regress as we add more sources in the future.
