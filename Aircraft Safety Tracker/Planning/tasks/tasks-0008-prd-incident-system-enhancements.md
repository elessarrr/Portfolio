## Relevant Files

- `app/models.py` - Will need to add fields to track data discrepancies (e.g., a JSON or boolean field on `Incident` or `IncidentSource`).
- `app/ingestion/dedupe.py` - Core matching and deduplication logic; will need to be updated to detect conflicting fatality counts and set discrepancy flags.
- `app/ingestion/importers/base.py` - Base importer; will need updates to automatically create missing `Aircraft` and `AircraftVariant` models when they don't exist.
- `scripts/import_data.py` - The regex logic for duplicate word stripping ("Boeing Boeing") needs to be applied here or in `scraper_utils.py`.
- `app/templates/components/global_incident_list.html` - The UI component that displays incident cards; needs updates to make the aircraft badge a link and display the new discrepancy warning flag.
- `app/templates/components/incident_list.html` - Similar to the global list, this component is used on the aircraft detail page and might need the same discrepancy flag updates.
- `tests/test_dedupe.py` - Will need new tests for the conflict detection logic.
- `tests/test_importer_base.py` - Will need new tests for the auto-creation of missing aircraft models.
- `tests/test_source_links.py` - Tests for the new clickable badge and warning flags.

### Notes

- Unit tests should be placed in the `tests/` directory following the existing pattern (e.g., `tests/test_dedupe.py`).
- Use `PYTHONPATH=. pytest tests/` to run tests. Running without a path executes all tests found by the Pytest configuration.

## Tasks

- [x] 1.0 Implement Discrepancy Detection and Warning UI
  - [x] 1.1 Update `Incident` model in `app/models.py` to include a `has_discrepancy` boolean column and a `discrepancy_details` JSON column to store the specific conflicts (e.g., `{"fatalities": [0, 5]}`). Add corresponding Alembic migration.
  - [x] 1.2 Modify `find_best_incident_match` and related logic in `app/ingestion/dedupe.py` to detect when an incoming incident has conflicting data (e.g., `fatalities`) compared to the existing matched `Incident`.
  - [x] 1.3 Update the `upsert` logic in `app/ingestion/importers/base.py` to set the `has_discrepancy` and `discrepancy_details` fields on the `Incident` when a conflict is detected during a merge.
  - [x] 1.4 Update `app/templates/components/global_incident_list.html` and `app/templates/components/incident_list.html` to display a warning icon (e.g., yellow triangle) next to the source badges if `has_discrepancy` is true. Include a tooltip or small popover showing the contents of `discrepancy_details`.
  - [x] 1.5 Write unit tests in `tests/test_dedupe.py` to verify that conflicting fatality counts correctly trigger the discrepancy logic and populate the JSON details.

- [ ] 2.0 Implement Aircraft Model Auto-Creation and Verification Logging
  - [ ] 2.1 Update `app/ingestion/importers/base.py` to automatically instantiate and `db.session.add()` a new `Aircraft` model if the parsed incident belongs to a Boeing or Airbus model that does not currently exist in the database.
  - [ ] 2.2 Create a lightweight logging mechanism (e.g., appending to `data/logs/model_verification.log`) that records the newly created model's name and ID. This fulfills the "Automated Backlog Verification" requirement without blocking the main import thread.
  - [ ] 2.3 Ensure the homepage dropdown in `app/templates/index.html` dynamically queries the `Aircraft` table (if it doesn't already) so that newly auto-published models immediately appear for users.
  - [ ] 2.4 Write unit tests in `tests/test_importer_base.py` to assert that importing an incident with an unknown Boeing/Airbus model correctly auto-creates the `Aircraft` record and writes to the verification log.

- [ ] 3.0 Implement Manufacturer/Model Duplicate Word Stripping
  - [ ] 3.1 Create a utility function `strip_duplicate_words` in `app/ingestion/importers/base.py` (or a shared utils file) that uses regex (e.g., `\b([A-Za-z]+)\s+\1\b`) to remove consecutive duplicate alphabetic words while preserving numbers (e.g., "Boeing Boeing 717" -> "Boeing 717", but "700-700" -> "700-700").
  - [ ] 3.2 Apply this stripping function to the `manufacturer`, `model_name`, and `variant_name` fields during the `parse()` or `validate()` phase of the importers (e.g., `NTSBImporter`, `FAAAIDSImporter`).
  - [ ] 3.3 Write unit tests in `tests/test_importer_base.py` to verify the regex correctly handles alphabetic duplicates, mixed case, and leaves numerical duplicates untouched.

- [ ] 4.0 Enhance Incident Card Navigation (Clickable Badges)
  - [ ] 4.1 Update `app/templates/components/global_incident_list.html` to wrap the existing aircraft badge (`{{ incident.aircraft.manufacturer }} {{ incident.aircraft.model_name }}`) in an `<a>` tag.
  - [ ] 4.2 Set the `href` attribute to `{{ url_for('main.aircraft_details', aircraft_id=incident.aircraft.id) }}` and add `target="_blank" rel="noopener noreferrer"` to fulfill the requirement of opening in a new tab.
  - [ ] 4.3 Apply appropriate Tailwind CSS hover states (e.g., `hover:underline`, `hover:bg-blue-200`) to visually indicate that the badge is interactive.
  - [ ] 4.4 Write a test in `tests/test_source_links.py` (or similar UI test file) to ensure the aircraft badge is rendered as a valid anchor tag with the correct `target="_blank"` attribute.