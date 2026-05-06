# Learnings From Errors

## 2026-03-30

- Error: Running `flask db upgrade` resulted in `duplicate column name: variant_name` on the local SQLite DB.
- Cause: The local SQLite database had manually drifted ahead (or a previous migration was partially applied without updating the `alembic_version` table) while Alembic thought it was at an older revision.
- Fix: Manually synchronized the Alembic version table using `sqlite3 ./data/aircraft_safety.db "UPDATE alembic_version SET version_num='8d2a1c4f0b17'"`, which skipped the already-applied changes and allowed the remaining migrations to run cleanly.
- Prevention: Avoid modifying schema directly in sqlite or if migrations are run from different branches, check `flask db history` vs local DB state. Use manual `UPDATE alembic_version` strictly as a local-dev repair tool.

## 2026-04-04

- Error: Export route tests failed with `InvalidRequestError: 'Incident.sources' does not support object population - eager loading cannot be applied`.
- Cause: `joinedload()` was introduced on relationships configured with `lazy='dynamic'` (`Incident.sources` and `Incident.system_tags`), which are query-based and incompatible with ORM eager population.
- Fix: Removed `joinedload()` from CSV export and kept compatible query behavior for dynamic relationships.
- Prevention: Before adding eager-loading strategies, verify relationship loader types (`dynamic`, `selectin`, `joined`) and use bulk query patterns for dynamic relationships instead of ORM eager loaders.

## 2026-03-31

- Error: AI summary could appear for an aircraft while Incident History showed no incidents.
- Cause: Summary generation and rendering only checked cached `aircraft.ai_summary`; there was no guardrail that validated incident existence in the `Incident` table.
- Fix: Added incident-existence guardrails in routes and summary rendering so generation is blocked without incidents, stale summaries are cleared, and the UI shows an explicit disabled message.
- Prevention: For all derived/cached AI outputs, gate generation and display on source-of-truth data availability, not only on cached text fields.

## 2026-03-22

- Error: Running `pytest -v` from project root failed with `ModuleNotFoundError: No module named 'app'`.
- Fix: Run tests with `PYTHONPATH=. pytest -v` so the project root is on Python's module search path.
- Prevention: Use `PYTHONPATH=. pytest -v` as the default local test command for this repository.

## 2026-04-05

- Error: Test execution failed immediately because `app/ingestion/importers/ntsb_importer.py` had an `IndentationError` and a malformed `upsert` control flow that bypassed existing-source upserts.
- Cause: A previous edit introduced incorrect indentation and effectively removed the `else` branch around dedupe/new-incident logic.
- Fix: Corrected indentation, restored proper `if existing_source ... else ...` flow, and re-ran importer and route/security tests.
- Prevention: Run targeted importer tests after any control-flow edit in ingestion modules and keep parser-safe checks (`python -m py_compile`) in CI pre-checks.

## 2026-04-05 (2)

- Error: Incidents from NTSB and FAA importers were created without an `aircraft_id`, resulting in orphaned records in the database.
- Cause: The abstract `DataSourceImporter` class defined `upsert()` but didn't provide a standardized way to resolve or auto-create `Aircraft` models, causing subclass implementations (like `NTSBImporter` and `FAAAIDSImporter`) to create `Incident` records with `aircraft_id=None`.
- Fix: Added a `resolve_aircraft` utility method to the base `DataSourceImporter` that extracts the manufacturer and model, strips duplicate words, and queries or auto-creates the `Aircraft` record. Updated the subclass `upsert` implementations to call `self.resolve_aircraft(parsed_record)` when creating an `Incident`.
- Prevention: When designing abstract base classes that handle related entities, provide shared utility methods for resolving foreign keys so subclasses don't miss crucial linking steps.

## 2026-04-18

- Error: `mypy app tests` failed in `NTSBImporter.parse()` with `Incompatible types in assignment` for `location`.
- Cause: `location` was inferred as `str` from formatted city/state text, then reassigned from `raw_record.get('location')`, which may be `None`.
- Fix: Declared `location` as `Optional[str]` before fallback assignment.
- Prevention: When a local variable can receive nullable payload fields, type it as `Optional[...]` up front to keep static typing aligned with runtime paths.

## 2026-04-18 (2)

- Error: New FAA SDR "no-match creates standalone incident" test failed with `assert None is not None`.
- Cause: The synthetic test row used `aircraft_model="B737"` but omitted a manufacturer marker, so it was filtered out by `fetch()` target-manufacturer gating before `parse()/upsert()` executed.
- Fix: Added `manufacturer="Boeing"` to the synthetic fixture row so the record reaches the no-match upsert path.
- Prevention: For importer tests that pass through `fetch()`, make synthetic fixtures satisfy upstream filter predicates (manufacturer gates, date windows) in addition to downstream parse/upsert fields.

## 2026-04-18 (3)

- Error: `test_import_data_all_continues_after_source_failure` stopped failing after wiring real importers into `import-data all`.
- Cause: The test monkeypatched `NoopImporter.run`, but the `NTSB` path now executes `NTSBImporter.run`, so the fault injection no longer hit the active code path.
- Fix: Updated the test to monkeypatch `NTSBImporter.run` directly.
- Prevention: When replacing stubs with concrete implementations, update tests to patch/assert the new execution points instead of legacy placeholders.

## 2026-04-19

- Error: Full test run failed in `test_null_date_incidents_do_not_break_sorting_on_detail_routes` with `UndefinedError: 'None' has no attribute 'strftime'` while rendering aircraft detail incidents.
- Cause: `incident_list.html` rendered `incident.date.strftime(...)` without a null guard, so introducing a null-date record to validate sort safety triggered template failure before route completion.
- Fix: Updated template date rendering to `incident.date.strftime('%Y-%m-%d') if incident.date else 'Unknown Date'`.
- Prevention: Any template date formatting used in list/detail pages should always include a null fallback, especially when historical data quality checks intentionally include missing dates.

## 2026-04-22

- Error: New backfill tests initially failed to import `scripts/backfill_aircraft_ids.py` as a normal package module.
- Cause: The `scripts/` directory is not a Python package and is designed for CLI entrypoints, so `from scripts...` imports are brittle in tests.
- Fix: Loaded the script module explicitly in tests using `importlib.util.spec_from_file_location(...)`, then imported test targets from that loaded module object.
- Prevention: For script-level logic that must be unit-tested, either expose importable functions in package modules or use explicit path-based imports in tests to avoid package-layout coupling.

## 2026-04-25

- Error: PRD validation logic mixed transport-level URL checks with payload-level API error checks, and suppression behavior was inconsistent across sections.
- Cause: Requirements used broad "HEAD validation" wording for all links, which misses body-level errors like NTSB `{"Error": ...}` responses; later suppression guidance also contradicted itself by allowing hidden/empty link elements in one section while requiring full omission in another.
- Fix: Updated PRD-0016 to require response-body validation for NTSB PDF links, kept reachability checks for docket/details URLs, and standardized suppression to "no link element rendered" across sections.
- Prevention: In future PRDs, separate protocol checks (status/reachability) from semantic checks (response payload validity), and run an internal consistency pass for UI behavior terms (`hide` vs `omit`) before approval.

## 2026-04-25 (2)

- Error: `test_search_returns_all_aircraft_without_limit` failed even after removing the limit(20) from search() - endpoint returned "No aircraft found" despite valid Aircraft data in test database.
- Cause: The search_results.html template only iterated over `grouped_results` (AircraftVariant entries), completely ignoring Aircraft without variants. When no variants matched the search query, grouped_results was empty even though matching Aircraft existed.
- Fix: Updated routes.py to add Aircraft without variants directly to grouped_results when no variants are found. Updated search_results.html to handle both Aircraft and AircraftVariant objects using `item.variant_name is defined` check.
- Prevention: When rendering search results that can include both parent entities and their variants, ensure the backend passes both types to the template and the template handles each appropriately.

## 2026-04-25 (3)

- Error: `test_search_no_duplicate_entries` failed with "Variant-A should appear exactly once" - found 2 instead of 1.
- Cause: The test used `html.count('Variant-A')` to verify uniqueness, but "Variant-A" appears twice per list item: once in the URL href attribute (`?variant=Variant-A`) and once in the display text. The HTML was correct - each variant only appeared once in the list.
- Fix: Changed test to use regex to count only href attributes containing `variant=Variant-A`, which accurately counts list items without false positives from URL and display text duplication.
- Prevention: When testing rendered HTML, count specific structural markers (like URLs) rather than raw text that can appear multiple times per element due to attributes and content. Use `href="[^"]*variant=Variant-A"` pattern to count link occurrences precisely.

## 2026-04-26

- Error: New search-order regression test failed with `DetachedInstanceError` when building expected URLs after leaving `app.app_context()`.
- Cause: The test accessed ORM instance attributes (`base.id`, `variant.id`) after the session/context closed, triggering lazy refresh on detached instances.
- Fix: Captured scalar IDs (`base_id`, `variant_id`) inside the active app context immediately after commit, then used those plain values in assertions.
- Prevention: In Flask/SQLAlchemy tests, never rely on ORM objects outside their active session scope; store primitive identifiers before exiting context blocks.

## 2026-04-26 (2)

- Error: Running `Planning/scripts/link_validator.py` failed with `sqlite3.OperationalError: no such column: incident_source.is_active`.
- Cause: The script was executed against a local DB before applying the new Phase 4 migration that adds `incident_source.is_active`.
- Fix: Ran `PYTHONPATH=. flask db upgrade` to apply revision `f4a9c2d1e7b3`, then re-ran the script successfully.
- Prevention: For any new script that depends on fresh schema columns, include a pre-run step in UAT: `flask db upgrade` before first execution in each environment.

## 2026-04-26 (3)

- Error: NTSB research query failed first with `sqlite3.OperationalError: unable to open database file`, then direct Python URL fetches failed (`ModuleNotFoundError: requests` and `HTTP Error 403` from `urllib`).
- Cause: Used an incorrect local DB path during ad-hoc analysis, and NTSB blocks some non-browser user-agent requests; the environment also does not include `requests` by default.
- Fix: Switched to web-verified evidence collection (`WebFetch`/`WebSearch`) and used `curl -A 'Mozilla/5.0'` for HTML inspection where needed.
- Prevention: For one-off diagnostics, confirm DB file path before running SQL and default to browser-like user-agent headers for NTSB endpoint inspection.

## 2026-04-26 (4)

- Error: Attempting to download NTSB `up22APR.zip` via guessed direct URLs produced HTML directory pages, causing `zipfile.BadZipFile`.
- Cause: `app.ntsb.gov/avdata` uses routed download links (`/FileDirectory/DownloadFile?...`) and direct/guessed file paths are not reliable in automation contexts.
- Fix: Parsed the index HTML first to discover canonical download-link patterns before any file processing attempts.
- Prevention: For public file directories, always extract and use exact `href` targets from the index page rather than constructing download URLs manually.

## 2026-04-26 (5)

- Error: Attempting to query ORM counts for Phase 1.5 failed with `ModuleNotFoundError: No module named 'flask'`.
- Cause: The current shell environment did not have project Python dependencies installed/activated.
- Fix: Used previously captured validated counts from the Phase 1.2 research note as the authoritative scope baseline for documentation updates.
- Prevention: Before ORM/Flask commands, run an environment readiness check (`python -c "import flask"`) and activate/install dependencies first when missing.

## 2026-04-26 (6)

- Error: Running the NTSB remediation script failed repeatedly due missing runtime deps (`flask`, `dotenv`, `thefuzz`, `bs4`) and macOS PEP668 blocked global `pip install -r requirements.txt`.
- Cause: The host Python is externally managed, and full requirements install in a fresh Python 3.14 venv failed on `psycopg2-binary` wheel/build constraints (`pg_config` missing).
- Fix: Created project-local `.venv`, installed requirements excluding `psycopg2-binary` (SQLite workflow), then installed missing runtime packages needed by app bootstrap.
- Prevention: For script execution in this repo, standardize on `.venv` + a SQLite-compatible dependency bootstrap path before running Flask app-context scripts.

## 2026-04-26 (7)

- Error: Focused test run (`python -m pytest`) failed with `No module named pytest` inside the new project `.venv`.
- Cause: Test tooling is not guaranteed in ad-hoc bootstrap flows where only runtime app dependencies are installed.
- Fix: Installed `pytest` into `.venv` and re-ran targeted tests successfully.
- Prevention: Add an explicit "developer-test bootstrap" step for this repo (`.venv` + `pip install pytest`) before validating code changes.

## 2026-04-26 (8)

- Error: `test_incident_card_with_asn_incident_source_link` failed after template migration with `assert None is not None`.
- Cause: The test still searched for hardcoded link text "Aviation Safety Network", but the template now renders the source label directly from `IncidentSource.source_name` (`ASN`).
- Fix: Updated the assertion to detect the rendered `ASN` label while keeping the href validation.
- Prevention: For template migration tests, assert on stable behavior (URL target/source mapping) and align text assertions with dynamic fields rather than legacy hardcoded labels.

## 2026-04-26 (9)

- Error: Follow-up test edit caused a second failure in `test_incident_card_with_source_url` by searching for `'ASN'` text in a case that intentionally uses `source_name='Aviation Safety Network'`.
- Cause: A broad text-based matcher was applied to multiple tests with different source labels.
- Fix: Switched both tests to match anchors by exact expected `href`, then assert attributes separately.
- Prevention: Prefer deterministic selectors (`href`, `aria-label`) over display text when template content can vary by source name.

## 2026-04-26 (10)

- Error: A long heredoc verification command was mangled in terminal execution and failed with `zsh: parse error near ')'`.
- Cause: Complex multiline quoting in a single command string is brittle in sandboxed terminal wrappers.
- Fix: Re-ran the verification using shorter `python -c` commands with simpler quoting.
- Prevention: Prefer short, focused commands over long heredocs when running app-context diagnostics through the sandbox terminal.

## 2026-04-26 (11)

- Error: A second FAA_AIDS audit command produced garbled terminal input and incomplete output while scanning all records.
- Cause: Long quoted sandbox command strings remain fragile when they contain many embedded quote transitions.
- Fix: Fell back to smaller, targeted verification commands (sample scan + explicit aggregate counters).
- Prevention: For DB audits, split analysis into short single-purpose commands and avoid deeply nested quoting.

## 2026-04-26 (12)

- Error: New `validate_incident_links` test for NTSB report-url-primary flow failed (`assert None == 200` for `log_entry.http_status`).
- Cause: `http_status` logging still used source-url-first semantics for `result='valid'`, so NTSB-valid rows did not capture `pdf_http`.
- Fix: Updated `http_status` assignment to use `pdf_http` when `source_name='NTSB'` and result is `valid`.
- Prevention: When adding source-specific validation branches, mirror source-specific behavior in audit/log fields (not only decision branches).

## 2026-05-02

- Error: New template verification test failed with `DetachedInstanceError` when calling `/aircraft/<id>` using `aircraft.id` outside `app.app_context()`.
- Cause: The ORM `Aircraft` instance became detached after leaving the SQLAlchemy session context; attribute access triggered a lazy refresh on a detached object.
- Fix: Captured `aircraft_id` as a primitive inside the active context and used that scalar in the request/assertions.
- Prevention: In Flask/SQLAlchemy tests, never carry ORM instances across context boundaries; store plain IDs immediately after commit for use outside the context.

- Error: Ad-hoc `/faq` route render check failed with `sqlite3.OperationalError: no such table: import_state`.
- Cause: The quick test-client script did not initialize the testing schema before rendering templates that depend on context processors reading `ImportState`.
- Fix: Initialized schema with `db.create_all()` in app context before issuing the request; `/faq` then rendered successfully.
- Prevention: For ad-hoc Flask route checks, always bootstrap the test DB schema first (or use pytest fixtures that do it automatically).

## 2026-05-03

- Error: Manual trigger of WA enrichment failed with `UNIQUE constraint failed: incident_source.source_name, incident_source.source_record_id` while inserting `MEDIA` with `source_record_id='www.bing.com'`.
- Cause: Enrichment used domain-only `source_record_id`, but `(source_name, source_record_id)` is globally unique; multiple incidents can share the same domain.
- Fix: Switched MEDIA `source_record_id` generation to `event_id + stable URL hash`, added duplicate-key skip handling around insert, and made CLI return non-zero when real errors occur.
- Prevention: Never use low-cardinality identifiers (domain/source label) as globally unique keys; derive IDs from incident-specific context plus deterministic hash.

- Error: Tier-1 enrichment accepted search-engine homepage URLs (`https://www.bing.com/`) as valid "articles", causing low-quality MEDIA links.
- Cause: Search candidates were validated only by HTTP/body checks, with no tier-domain policy filter; Tier-1 query also used only `site:aviation-herald.com` and missed `avherald.com`.
- Fix: Added pre-validation candidate filtering (reject search engines/root pages, enforce tier domain allowlists) and updated Tier-1 query to include both `site:avherald.com` and `site:aviation-herald.com`.
- Prevention: For search-based ingestion, enforce semantic URL filters before network validation and encode domain intent per tier in code/tests.

- Error: After the first filter patch, Tier-3 still accepted low-signal portal URLs (for example `https://www.msn.com/play?...`) as "found" coverage.
- Cause: Domain/path quality rules blocked search engines but not generic portal endpoints that can return dynamic non-article pages with enough HTML length to pass body checks.
- Fix: Added explicit low-signal portal/path filtering (`msn.com`, `/play`, `/search`) before URL validation.
- Prevention: Keep a maintained denylist for known non-article portals and review enrichment logs for repetitive identical URLs across many incidents.

- Error: Follow-up live run still returned repeated `https://www.microsoft.com/bing?...` links as Tier-3 "found" results.
- Cause: The first portal denylist missed Microsoft Bing utility endpoints hosted on `microsoft.com`.
- Fix: Added additional filters for Microsoft utility endpoints on `*.microsoft.com` (`/bing`, `/fwlink`).
- Prevention: Expand denylist iteratively based on observed repetitive false positives in enrichment logs.

## 2026-05-06

- Error: Full suite failed with `No such command 'mark-wa-ntsb-inactive'` in NTSB CLI tests.
- Cause: The `mark-wa-ntsb-inactive` command block was missing from `app/ingestion/cli.py`, so Click could not register it under `import-data`.
- Fix: Restored the `@import_data.command('mark-wa-ntsb-inactive')` handler with dry-run/apply flow and WA pattern filtering (`LIKE '_____WA%'`).
- Prevention: After CLI refactors, run `flask import-data --help` plus command-specific `--help` checks to verify registration before running the full suite.
