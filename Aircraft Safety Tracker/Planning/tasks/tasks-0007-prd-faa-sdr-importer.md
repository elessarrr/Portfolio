## Relevant Files

- `app/ingestion/importers/faa_sdr_importer.py` - Implements FAA SDR fetch flow with tenacity retries, Boeing/Airbus filtering, and incremental filtering via `self.start_date`.
- `tests/test_faa_sdr_importer.py` - Unit tests for the new `FAASDRImporter` to ensure fetching, parsing, and retry logic works correctly.
- `app/ingestion/cli.py` - Needs modification to replace the `NoopImporter` stub for `faa-sdr` with the new `FAASDRImporter`.
- `requirements.txt` - Updated to include the `tenacity` library for exponential backoff retry behavior.

## Progress

- 🟡 In Progress — 35% complete (8/23 tasks checked)

### Notes

- The importer must inherit from `DataSourceImporter` defined in `app/ingestion/importers/base.py` to ensure consistent state tracking and logging.
- `tenacity` is the standard Python library for implementing retry logic and should be used to handle rate limits and network errors when calling the FAA SDR database.
- The `parse()` method of the importer needs to accurately map raw FAA SDR data to the keys expected by the application's incident model, paying special attention to date formatting and aircraft model normalization.
- FAA SDR search target confirmed: `https://drs.faa.gov/browse/excelExternalWindow/` (publicly reachable and returned HTTP 200 during verification from this environment).

## Tasks

- [ ] 1.0 Setup and Infrastructure
  - [x] 1.1 Update `requirements.txt` to include the `tenacity` library.
  - [x] 1.2 Create the new file `app/ingestion/importers/faa_sdr_importer.py`.
  - [x] 1.3 Define the `FAASDRImporter` class inheriting from `DataSourceImporter`.
  - [x] 1.4 Set up basic class attributes (`source_name = 'FAA_SDR'`, API endpoints, constants).
- [ ] 2.0 Implement FAA SDR Data Fetching
  - [x] 2.1 Research and document the exact FAA SDR public API endpoint or search form URL to target.
  - [x] 2.2 Implement the `fetch()` method in `FAASDRImporter` to query the FAA database specifically for Boeing and Airbus records.
  - [x] 2.3 Add `tenacity` retry logic to `fetch()` to handle 429 and 5xx errors with exponential backoff.
  - [x] 2.4 Implement incremental fetching logic utilizing `self.start_date` (populated from `ImportState.last_successful_at`).
- [ ] 3.0 Implement Data Parsing and Validation
  - [ ] 3.1 Implement the `parse()` method to extract and map raw FAA fields (Date, Aircraft Model, Narrative, Operator, Control Number) to the standard dictionary format expected by the app.
  - [ ] 3.2 Ensure the aircraft model name is normalized (e.g., stripping excess whitespace, formatting "B737" to "Boeing 737") so it matches existing database records.
  - [ ] 3.3 Implement `validate()` to skip records with missing dates or malformed IDs, while ensuring no severity-based filtering is applied.
- [ ] 4.0 Implement Data Upsertion and Deduplication
  - [ ] 4.1 Implement the `upsert()` method to create or find existing `IncidentSource` records based on the SDR Control Number.
  - [ ] 4.2 Feed the parsed SDR record into `record_dedupe_decision` and `attach_source_to_incident` to trigger the deduplication pipeline against existing ASN records.
  - [ ] 4.3 Verify that if no match is found, a new standalone `Incident` is created.
- [ ] 5.0 CLI Integration and Testing
  - [ ] 5.1 Modify `app/ingestion/cli.py` to replace `NoopImporter` with `FAASDRImporter` in the `import_faa_sdr` and `import_all` commands.
  - [ ] 5.2 Create `tests/test_faa_sdr_importer.py` to mock the FAA API and test the `fetch`, `parse`, and `upsert` methods.
  - [ ] 5.3 Run `pytest` to ensure all tests pass.
  - [ ] 5.4 Execute a dry run of `flask import-data faa-sdr` locally to verify successful live data ingestion and state tracking without IP bans.
