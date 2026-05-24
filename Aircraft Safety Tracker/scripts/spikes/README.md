# FAA AIDS URL spike scripts

Time-boxed research for [PRD 0001](../../Planning/tasks/0001-prd-faa-aids-per-record-url-spike.md).

## Environment

| Variable | Purpose |
|----------|---------|
| `FAA_AIDS_ZIP_URL_TEMPLATE` | Optional. If unset, spike uses ASIAS direct URL for `a2020_26.zip` (see inventory script). |
| `DATABASE_URL` / Flask config | SQLite path to `data/aircraft_safety.db` (read-only recommended). |

## Rate limits

- **≤1 HTTP request/second** to `faa.gov` and `asias.faa.gov`.
- User-Agent: `AircraftSafetyTracker/1.0 (faa-aids-url-spike; +https://github.com/)`

## SQLite

Run **one** process at a time against `data/aircraft_safety.db` (no parallel Flask imports).

## Commands (repo root)

```bash
PYTHONPATH=. python scripts/spikes/faa_aids_url_inventory.py
PYTHONPATH=. python scripts/spikes/faa_aids_export_sample.py
PYTHONPATH=. python scripts/spikes/faa_aids_url_validate.py
PYTHONPATH=. python scripts/spikes/faa_aids_url_stability.py   # re-run ≥24h after validate
```

Outputs land under `Planning/spike-reports/`.
