# 0004 PRD: Full Boeing/Airbus Model Coverage from ASN

## 1. Introduction / Overview
Today, the app shows only a subset of Boeing/Airbus aircraft, and many expected models/variants are missing. The primary goal of this work is to ingest the full Boeing and Airbus aircraft catalog (all entries ASN exposes for those manufacturers) and keep it up to date automatically, using the existing ASN ingestion approach already present in this repo.

## 2. Goals
- Achieve near-complete Boeing + Airbus catalog coverage from ASN type indexes.
- Preserve the existing “type (series) → incidents” behavior, and add consistent variant coverage derived from ASN data.
- Keep ASN catalog + incident import fresh automatically: if last successful sync is older than 7 days, trigger a sync on app startup (non-blocking).
- Provide a clear sync report (counts, deltas, failures) for confidence and debugging.

## 3. User Stories
- As a user, when I search “Boeing” or “Airbus”, I can browse all relevant aircraft types and their variants.
- As a user, when I search a variant name (e.g., “737-800” or “A320-232”), I can find the correct aircraft quickly.
- As an operator, I can run an ASN sync manually and see a summary of what changed.
- As an operator, the app automatically refreshes ASN data weekly without manual intervention.

## 4. Functional Requirements

1. **Catalog discovery (ASN type indexes)**
   1.1 The system must crawl ASN type index pages for Boeing and Airbus and discover all type pages.
   1.2 The system must persist the discovered type list (name + ASN URL) in a durable store.
   1.3 The system must handle manufacturer naming inconsistencies (e.g., spacing/hyphenation, “Airbus” variations) without dropping valid entries.

2. **Incident + variant ingestion (reuse existing pipeline)**
   2.1 The system must continue scraping incidents for each discovered ASN type page using existing scraper utilities.
   2.2 The system must import incidents into the database using the existing importer pattern.
   2.3 The system must create and/or update variant records derived from ASN’s aircraft type column and/or incident details (e.g., `variant_name` already extracted by the scraper).
   2.4 The system must ensure ingestion is idempotent (re-running sync does not create duplicates).

3. **Completeness + reconciliation reporting**
   3.1 The system must produce a coverage report per manufacturer after each sync, including:
       - number of discovered ASN types
       - number imported into `Aircraft`
       - number of variants created/updated
       - number of incidents imported/updated
       - parsing/skipping errors (with counts)
   3.2 The system must store the last successful sync timestamp.

4. **Auto-sync on startup (weekly, non-blocking)**
   4.1 On app startup, the system must check when the ASN sync last ran successfully.
   4.2 If last successful sync is older than 7 days, the system must trigger a sync in the background.
   4.3 The system must prevent overlapping sync runs (e.g., lockfile / DB flag) to avoid corrupting data.
   4.4 The system must not block serving web requests while a sync is running.

5. **Manual sync trigger**
   5.1 The system must provide a manual command/script to run the ASN sync.
   5.2 The system must support a “dry run / report-only” mode that does discovery + diff reporting without writing to the DB.

6. **UI expectations**
   6.1 The search dropdown must display both aircraft types and variants when relevant.
   6.2 The “Series / Models” view must populate the Models column with discovered variants for each Series.

## 5. Non-Goals (Out of Scope)
- Ingesting manufacturers beyond Boeing and Airbus.
- Real-time scraping on every search request.
- Full legal/commercial data licensing negotiation (we will scrape politely; see Open Questions).

## 6. Design Considerations (Optional)
- In the search results UI, treat “Series” as the base aircraft type (e.g., “Boeing 737”), and “Models” as variants (e.g., “737-800”, “737 MAX 8”).
- When variants are not available for a series, show a clear “No variants captured yet” empty state rather than leaving the Models column blank.

## 7. Technical Considerations (Optional)
- Reuse existing ASN scrapers and shared parsing utilities:
  - `scripts/scrape_boeing.py`, `scripts/scrape_airbus.py`
  - `scripts/scraper_utils.py`
  - `scripts/import_data.py`
- Extend the importer to upsert `AircraftVariant` records using `variant_name` already emitted by the scraper.
- Add a small “sync state” mechanism to store `last_successful_asn_sync_at` (either a DB table or a local file under `data/`).
- Implement a lock to prevent concurrent runs (prefer a lockfile under `data/` for minimal DB impact).
- Apply rate limiting, retries, and caching; keep requests respectful to ASN.

## 8. Success Metrics
- Catalog completeness: `Aircraft` count for Boeing + Airbus aligns with ASN type index count (target ≥ 95%).
- Variant coverage: for top families (737, 747, 777, A320, A330, A350), variants appear in UI.
- Sync reliability: weekly auto-sync runs successfully without manual intervention.
- Sync performance: completes within an acceptable time window (target ≤ 15 minutes on a dev machine; configurable).

## 9. Open Questions
1. Do we want to include non-commercial Airbus entries (e.g., Airbus Helicopters) if ASN lists them under Airbus?
2. Where should we store “last successful sync” and “lock” state: DB table (more robust) or lockfile (minimal schema changes)?
3. Should auto-sync on startup be enabled by default in dev only, or also in production?

