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

### Notes

- API keys must be provided via environment variables / `.env` and never committed.

## Tasks

- [ ] 1.0 Extend database schema for multi-source ingestion
-  - [ ] 1.1 Add `ImportLog` model/table for per-run tracking and metrics.
-  - [ ] 1.2 Add `JASCMapping` model/table for mapping JASC codes to `SystemTag`.
-  - [ ] 1.3 Extend `IncidentSource` fields to match PRD (record ID + confidence + timestamps).
-  - [ ] 1.4 Add indexes/constraints needed for source filtering and dedupe lookups.
-  - [ ] 1.5 Add migration(s) for schema updates and verify both SQLite + Postgres paths.
- [ ] 2.0 Create importer framework + CLI entrypoints + per-source import state
-  - [ ] 2.1 Create `DataSourceImporter` base class with standardized hooks (fetch, parse, validate, upsert).
-  - [ ] 2.2 Implement per-source state tracking (last successful import timestamp + counts + errors).
-  - [ ] 2.3 Add `flask import-data` CLI group with per-source commands and date/year parameters.
-  - [ ] 2.4 Implement structured import logging to `data/logs/import_YYYYMMDD_HHMMSS.log`.
-  - [ ] 2.5 Ensure failures in one source do not block remaining sources.
- [ ] 3.0 Implement NTSB importer (API + bulk download parsing)
-  - [ ] 3.1 Implement NTSB API client with batching and backoff on 429.
-  - [ ] 3.2 Implement bulk download fetch + unzip + parsing for tab-delimited files.
-  - [ ] 3.3 Normalize NTSB fields into `Incident` + `IncidentSource` (probable cause, findings, injuries, etc.).
-  - [ ] 3.4 Store NTSB PDF report URL and key identifiers in `IncidentSource`.
-  - [ ] 3.5 Add validation for required fields and date range (1985–2025).
- [ ] 4.0 Implement FAA AIDS + FAA SDR importers (including JASC mapping to SystemTag)
-  - [ ] 4.1 Implement FAA AIDS downloader/parser (tab-delimited zip) with year/month support.
-  - [ ] 4.2 Map FAA AIDS fields into `Incident` + `IncidentSource` (narrative, findings, phase, etc.).
-  - [ ] 4.3 Implement FAA SDR annual CSV downloader/parser with year parameter.
-  - [ ] 4.4 Parse JASC code fields and validate against expected format.
-  - [ ] 4.5 Apply `JASCMapping` to create `SystemTag` associations (and fallback “Unknown System”).
-  - [ ] 4.6 Seed initial JASC-to-system mappings and add admin workflow for unmapped codes.
- [ ] 5.0 Implement deduplication/linking and UI source attribution (badges, filters, freshness)
-  - [ ] 5.1 Implement dedupe matching rules (exact + fuzzy) and persist merge/link decisions.
-  - [ ] 5.2 Choose canonical record rules (NTSB preferred) and attach other sources via `IncidentSource`.
-  - [ ] 5.3 Add “Data Sources” filter behavior end-to-end (query + UI checkboxes).
-  - [ ] 5.4 Render source badges per incident row and show “Also reported by …” links.
-  - [ ] 5.5 Display per-source “Last updated” timestamps in footer.
-  - [ ] 5.6 Add tests for importer validation, source linking, and source filtering.
