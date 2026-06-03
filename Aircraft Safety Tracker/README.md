# Aircraft Safety Tracker

A full-stack web application that aggregates and cross-references aviation incident data from three public government and industry databases — Aviation Safety Network (ASN), NTSB, and FAA AIDS — across 153 Boeing and Airbus aircraft models.

> **Portfolio / educational demo.** Incident counts don't indicate aircraft design quality. See disclaimer at the bottom.

---

## What it does

Search for a Boeing or Airbus model, view its full incident history, and click through to the official source record. Every **Details** link is verified before display — the app won't show a link if the underlying page is a dead end, an unreleased investigation, or an empty JavaScript shell.

**Live data:**
- **12,592 incidents** across **153 aircraft models**
- **5,523** incidents with Aviation Safety Network source links (scraped baseline)
- **603** NTSB investigation records (US accidents with verified docket/CAROL URLs)
- **6,453** FAA AIDS records (ASIAS brief report URLs, page-18 verified)
- AI-generated safety summaries per aircraft model (DeepSeek API)

---

## Architecture

Flask monolith — application factory pattern, SQLAlchemy ORM, Jinja2 + HTMX frontend. PostgreSQL in production (Railway), SQLite locally.

```
┌─────────────────────────────────────────────────────────┐
│  Ingestion pipeline (offline scripts)                   │
│                                                         │
│  ASN scrape → import_data.py ─────────────────────┐    │
│  NTSB export → viability audit → dedupe → import ─┤    │
│  FAA export → mapping → dedupe → import ──────────┘    │
│                               ↓                         │
│              aircraft_safety_v3.db / PostgreSQL         │
└─────────────────────────────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────┐
│  Flask app (app/)                                       │
│                                                         │
│  routes.py → link_picker.py → IncidentSource            │
│           → incident_visible() → templates (HTMX)       │
└─────────────────────────────────────────────────────────┘
```

**Key design decisions:**

- **One verified link per incident.** Priority: ASN → NTSB → FAA. `pick_primary_href()` in `app/link_picker.py` resolves at render time from pre-validated `IncidentSource` rows.
- **`is_active` as the gate.** URL viability audits write back a boolean; the UI never shows a Details link for inactive sources.
- **No N+1 on incident lists.** Sources batch-loaded per page via `_load_sources_by_incident_id()` in `app/routes.py`.
- **Ask-before-write scripts.** All DB-modifying ingestion scripts support `--dry-run` before `--apply`.

---

## Data sources & ingestion

### Aviation Safety Network (ASN)
Scraped via `scripts/scrape_boeing.py` / `scrape_airbus.py`. Stored directly on `Incident.asn_url`. Family/aggregate rows (e.g. "Boeing 737 family") are skipped at import to avoid URL deduplication collisions with variant pages.

### NTSB
Exported from NTSB bulk data, audited for URL viability, deduplicated against the ASN baseline, and imported via `scripts/ntsb_bulk_import.py` with a make/model mapping gate.

Two classes of dead link required body-content checks (HTTP status alone is insufficient):
- **Unreleased dockets** — HTTP 200 with "The docket for this investigation has not been released"
- **CAROL empty SPA shells** — HTTP 200 with `<main id="root"></main>` and no rendered content

### FAA AIDS (Accident and Incident Data System)
Sourced from the FAA's ASIAS portal. 6,466 Boeing/Airbus records imported, each URL verified as a working "brief report" page (ASIAS page 18, `AP_BRIEF_RPT_VAR`) rather than a search prefill (page 12, which still requires an extra user click).

The audit pipeline (`scripts/audit_faa_aids_urls.py`) runs a liveness probe on the ASIAS homepage before checking individual records — a site-wide CDN outage would otherwise classify all 6,000+ records as dead. Concurrent request volume is throttled to avoid triggering rate limits that produce false failures.

After import, 246 FAA records that duplicated existing ASN baseline incidents were soft-deleted (`is_active=False`) via `scripts/audit_faa_baseline_overlap.py`.

---

## URL audit engine

`url_audit/` is a portable Python package (built in PRD 0008) that handles the common pattern of:

1. Bulk HTTP checks with concurrency + per-request jitter
2. Classification into JSONL buckets (`working`, `not_working`, etc.)
3. Retry passes with overlay merge (newer result wins per record ID)
4. Optional DB write-back with `--dry-run` / `--apply`

FAA-specific rules (three-tier bucket classification, liveness gate, page-18 vs page-12 distinction) are implemented on top of this generic engine.

---

## Tech stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.8+, Flask 3, Flask-SQLAlchemy, Flask-Migrate, Flask-Caching |
| Frontend | Jinja2, HTMX, Tailwind CSS (CDN) |
| Database | PostgreSQL (prod), SQLite (dev) |
| HTTP / scraping | httpx, BeautifulSoup |
| AI summaries | DeepSeek OpenAI-compatible API |
| Testing | pytest (153 tests) |
| Deployment | Railway (Gunicorn) |
| Search | PostgreSQL `pg_trgm` (fuzzy model search) |
| Deduplication | `thefuzz` token-set ratio for cross-source incident matching |

---

## Local development

```bash
# 1. Install
git clone <repo-url>
cd "Aircraft Safety Tracker"
pip install -r requirements.txt

# 2. Configure
cp .env.example .env
# Add DEEPSEEK_API_KEY for AI summaries (optional)

# 3. Build ASN baseline (required — creates data/aircraft_safety_v3.db)
PYTHONPATH=. python scripts/scrape_boeing.py
PYTHONPATH=. python scripts/scrape_airbus.py
PYTHONPATH=. python scripts/import_data.py

# 4. Run
export FLASK_APP=run.py DATABASE_URL="sqlite:///$(pwd)/data/aircraft_safety_v3.db"
flask run -p 5003

# 5. Run tests
PYTHONPATH=. pytest -q
```

> **Always run Flask and pytest from the `Aircraft Safety Tracker/` directory**, not the parent `Portfolio/` repo root.

NTSB and FAA AIDS data are not re-importable from this repo alone (they require access to the source exports). The ASN scrape provides a fully working baseline.

---

## Project structure

```
app/
├── routes.py                    # HTTP routes + HTMX endpoints
├── models.py                    # Aircraft, Incident, IncidentSource
├── link_picker.py               # Details link priority + validation
├── ingestion/
│   ├── importers/               # NTSBImporter, FAAAIDSImporter
│   ├── url_builders/            # ntsb.py, faa_aids.py, viability checks
│   ├── dedupe/                  # Cross-source deduplication scoring
│   └── faa_baseline_overlap.py  # FAA vs ASN/NTSB overlap audit + UI gate
scripts/
├── scrape_boeing.py / scrape_airbus.py
├── audit_faa_aids_urls.py       # Concurrent URL audit with liveness probe
├── merge_faa_aids_audit_overlay.py
├── migrate_faa_aids_urls_to_brief.py
├── apply_faa_audit_buckets_to_db.py
└── ntsb_bulk_import.py
url_audit/                       # Portable URL audit engine (PRD 0008)
data/
├── aircraft_safety_v3.db        # Local SQLite (not committed)
└── config/
    ├── ntsb_make_model_to_aircraft.jsonl
    └── faa_aids_make_model_to_aircraft.jsonl
```

---

## What's not in scope (deliberate decisions)

- **FAA SDR (Service Difficulty Reports)** — named in the link priority chain but not imported; the source endpoint has reliability issues and SDRs are maintenance flags rather than incidents.
- **Consumer-facing product** — this is a portfolio/technical demo. The liability considerations around presenting raw incident counts to general users are real (see the `Planning/LinkedIn-post-v2-2026-06-03.md` post for context).
- **Incident unification across sources** — NTSB and FAA sources are stored as separate incident rows rather than merged onto ASN rows. True cross-source event matching would require fuzzy deduplication with a higher false-negative risk than was acceptable here.

---

## Disclaimer

Educational and portfolio demonstration only. Incident data is complex — counts do not indicate aircraft design quality, and many incidents involve factors unrelated to the aircraft itself (weather, ATC, pilot error, etc.). Not intended for operational safety assessment.

---

## License

MIT
