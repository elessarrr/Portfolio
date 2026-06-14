## Relevant Files

- `Planning/tasks/0010-prd-asrs-contributing-factors-layer.md` - Source PRD.
- `app/models.py` - `AsrsReport` SQLAlchemy model.
- `migrations/versions/d4e5f6a7b8c9_add_asrs_report.py` - Alembic migration for `asrs_report`.
- `app/ingestion/asrs_aircraft_match.py` - Heuristic ASRS make/model → `Aircraft.id` matcher + JSONL overrides.
- `app/ingestion/asrs_import.py` - HF/CSV row normalisation and idempotent import.
- `app/services/asrs.py` - `get_asrs_profile()` aggregation and factor buckets.
- `app/routes.py` - Passes `asrs_profile` to aircraft detail template.
- `app/templates/components/asrs_profile_card.html` - Crew Safety Reports UI card.
- `app/templates/aircraft.html` - Card placement below summary, above incidents.
- `scripts/import_asrs.py` - CLI: `--source huggingface`, `--csv`, `--csv-dir`, `--dry-run`/`--apply`.
- `app/ingestion/asrs_coverage.py` - Ship-gate coverage summary builder.
- `scripts/README_asrs_refresh.md` - HF-first refresh runbook.
- `requirements-ingest.txt` - Optional `datasets` for HF import only.
- `data/config/asrs_make_model_to_aircraft.jsonl` - Manual make/model override map.
- `data/logs/asrs_coverage_summary.json` - Coverage gate artifact (generated).
- `tests/test_asrs.py` - ASRS unit + route tests.
- `tests/fixtures/asrs_sample.csv` - DBOL-shaped CSV fixture for import tests.
- `Planning/master_context_documents/mcd_2026-06-18_asrs-contributing-factors-layer.md` - Architecture MCD.

### Notes

- Run tests: `PYTHONPATH=. pytest -q`
- HF import: `pip install -r requirements-ingest.txt && PYTHONPATH=. python scripts/import_asrs.py --source huggingface --apply`
- Ship gate: ≥10 catalog aircraft with `n > 0` after HF import (PRD §8).

## Tasks

- [x] 1.0 Schema — `asrs_report` table
  - [x] 1.1 Add `AsrsReport` model (`acn` unique, nullable `aircraft_id` FK)
  - [x] 1.2 Alembic migration `d4e5f6a7b8c9_add_asrs_report.py`

- [x] 2.0 Ingestion — HF primary, DBOL CSV gap-fill
  - [x] 2.1 `app/ingestion/asrs_import.py` (HF columns, CSV fallback, idempotent `acn`)
  - [x] 2.2 `scripts/import_asrs.py` CLI (`--dry-run` / `--apply`)
  - [x] 2.3 `app/ingestion/asrs_aircraft_match.py` + `data/config/asrs_make_model_to_aircraft.jsonl`
  - [x] 2.4 `requirements-ingest.txt` + `scripts/README_asrs_refresh.md`

- [x] 3.0 App — aggregate profile + aircraft page card
  - [x] 3.1 `app/services/asrs.py` — factor buckets, `get_asrs_profile()`
  - [x] 3.2 `asrs_profile_card.html` (n=, bars, disclaimers, hide when n=0)
  - [x] 3.3 Wire `aircraft_details` route + `aircraft.html` placement

- [x] 4.0 Tests — import path + idempotency
  - [x] 4.1 Core tests: matcher, profile aggregation, route shows card (`tests/test_asrs.py`)
  - [x] 4.2 CSV fixture + import dry-run/apply tests
  - [x] 4.3 Idempotency test: second import skips duplicates
  - [x] 4.4 `export_asrs_coverage.py` unit test (`app/ingestion/asrs_coverage.py`)

- [x] 5.0 Data load — HF import on v3 DB + coverage gate
  - [x] 5.1 Install ingest deps; run `import_asrs.py --source huggingface --apply` (via `.venv-asrs`)
  - [x] 5.2 Generate `data/logs/asrs_coverage_summary.json`; **53 aircraft** with n>0 (gate PASS)
  - [x] 5.3 Matcher tuning not required for gate
  - [x] 5.4 Re-run import: duplicate=47723, imported=0 (idempotent)

- [x] 6.0 Sign-off — docs, PRD close, MCD
  - [x] 6.1 Resolve OQ-6 in PRD; status Ready for review
  - [x] 6.2 `Planning/master_context_documents/mcd_2026-06-18_asrs-contributing-factors-layer.md`
  - [x] 6.3 Update compound doc (HF primary path)
  - [x] 6.4 JOURNAL entry; full `pytest -q` green
