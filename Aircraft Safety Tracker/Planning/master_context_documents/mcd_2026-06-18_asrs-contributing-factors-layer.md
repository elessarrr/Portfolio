# Master Context Document — ASRS Contributing Factors Layer (PRD 0010)

**Date:** 2026-06-18  
**Branch:** `v4-incorporating-FAA-AIDS-links` (or current ASRS work branch)

## Summary

Adds a **Crew Safety Reports** aggregate panel on aircraft detail pages using NASA ASRS data imported from the public Hugging Face snapshot `elihoole/asrs-aviation-reports` (~47.7k rows). ASRS rows are **not** linked to individual `Incident` records — aggregation is at `Aircraft.model_name` level only.

## Data flow

```
Hugging Face elihoole/asrs-aviation-reports (primary)
  → scripts/import_asrs.py --source huggingface --apply
  → asrs_report table (dedupe on acn)
  → asrs_aircraft_match.py (heuristic + optional JSONL overrides)
  → aircraft_id FK (nullable for unmatched)

Optional gap-fill: DBOL CSV → import_asrs.py --csv / --csv-dir

Aircraft detail page:
  → get_asrs_profile(aircraft_id) in app/services/asrs.py
  → asrs_profile_card.html (hidden when n=0)
```

## New modules

| Module | Role |
|--------|------|
| `app/models.py` → `AsrsReport` | Raw ASRS rows |
| `app/ingestion/asrs_import.py` | HF/CSV normalisation, idempotent insert |
| `app/ingestion/asrs_aircraft_match.py` | Make/model → `Aircraft.id` |
| `app/ingestion/asrs_coverage.py` | Ship-gate coverage summary |
| `app/services/asrs.py` | Factor buckets + `get_asrs_profile()` |
| `scripts/import_asrs.py` | CLI ingest |
| `scripts/export_asrs_coverage.py` | Write `data/logs/asrs_coverage_summary.json` |

## Migration

`migrations/versions/d4e5f6a7b8c9_add_asrs_report.py` — table `asrs_report`, unique `acn`.

## Ingest dependencies

- Runtime Flask app: **no** `datasets` dependency
- Ingest only: `requirements-ingest.txt` → `datasets`
- Local venv workaround if conda pyarrow broken: `.venv-asrs/` (gitignored)

## Ship gate (2026-06-18 run)

From `data/logs/asrs_coverage_summary.json`:

- **total_rows:** 47,723
- **matched_rows:** 17,226 (36% — remainder unmatched make/model strings)
- **aircraft_with_data:** 53 (gate ≥10: **PASS**)
- Top: Boeing 737 (2552), 737-800 (1662), 737-700 (1441), Airbus A320 (1404)

## UI placement

`aircraft.html`: summary card → **ASRS card** → incident table.

## Non-goals (v1)

- Per-incident ASRS linking
- LLM narrative synthesis
- DBOL scraping / hidden API
- Deep-linked DBOL URLs (POST form)

## Related

- PRD: `Planning/tasks/0010-prd-asrs-contributing-factors-layer.md`
- Tasks: `Planning/tasks/tasks-0010-prd-asrs-contributing-factors-layer.md`
- Compound: `docs/solutions/architecture-patterns/asrs-aggregate-layer-dbol-acquisition.md`
