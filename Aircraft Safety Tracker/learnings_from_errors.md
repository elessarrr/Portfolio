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
