# ASRS data refresh

Primary source: [elihoole/asrs-aviation-reports](https://huggingface.co/datasets/elihoole/asrs-aviation-reports) (~47.7k DBOL-derived reports).

## One-time setup

```bash
pip install -r requirements-ingest.txt
flask db upgrade head
# If conda pyarrow is broken:
python3 -m venv .venv-asrs && .venv-asrs/bin/pip install -r requirements-ingest.txt Flask Flask-SQLAlchemy python-dotenv thefuzz Flask-Migrate Flask-Caching Flask-WTF email-validator httpx openai beautifulsoup4 python-dateutil
```

Use `.venv-asrs/bin/python` instead of `python` below when using the venv.

## Bulk import (recommended)

```bash
PYTHONPATH=. python scripts/import_asrs.py --source huggingface --dry-run
PYTHONPATH=. python scripts/import_asrs.py --source huggingface --apply
```

Idempotent on `acn`. Re-running skips duplicates.

After matcher rule changes, recompute assignments without re-downloading HF:

```bash
PYTHONPATH=. python scripts/remap_asrs_aircraft_ids.py --dry-run
PYTHONPATH=. python scripts/remap_asrs_aircraft_ids.py --apply
PYTHONPATH=. python scripts/export_asrs_coverage.py
```

## Gap-fill from DBOL CSV

When a catalog model has no HF matches, export from [ASRS DBOL](https://asrs.arc.nasa.gov/search/database.html):

1. Query a **specific** make/model (not "All Series")
2. Export CSV if ≤ 5,000 rows (shard by date if larger)
3. Import:

```bash
PYTHONPATH=. python scripts/import_asrs.py --csv data/raw/asrs/B737-800.csv --apply
PYTHONPATH=. python scripts/import_asrs.py --csv-dir data/raw/asrs/ --apply
```

## Overrides

Edit `data/config/asrs_make_model_to_aircraft.jsonl` for edge-case mappings.

## Notes

- `datasets` is ingest-only — not required for Flask runtime
- HF snapshot is a subset of full ASRS; UI discloses this
- NASA staff extract was attempted 2026-06-04; no response — not a dependency
