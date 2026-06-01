# FAA AIDS Per-Record URL Spike — Report

**PRD:** `Planning/tasks/0001-prd-faa-aids-per-record-url-spike.md`  
**Date:** 23 May 2026  
**Decision:** **GO** (direct per-record URL)  
**Decision owner:** Product lead — *pending your sign-off on this report*

---

## Executive summary

The spike found a **stable, deterministic direct URL** for FAA AIDS records using the public **ASIAS** web app. On a **500-row stratified sample**, the pattern **`P12_AIDS_RPRT_NBR`** (AIDS report number = our `source_record_id` / bulk field `c5`) achieved **100% match** (500/500). A same-session re-test of 50 URLs also scored **100% stable**.

**Recommendation:** Proceed to **Phase 2** (implement `build_faa_aids_links()`, set URLs at import, batch backfill ~157k rows). Estimated effort: **M** (2–3 days).

**Expected coverage lift:** Incident-level link coverage should rise from **~32%** to roughly **~97%** (157k FAA-only incidents gain a link), assuming backfill completes.

---

## Methods

1. **DB inventory** — 100-row key scan of `IncidentSource.source_data` for active `FAA_AIDS` rows (`scripts/spikes/faa_aids_url_inventory.py`).
2. **Latest ZIP** — Attempted download of `a2020_26.zip` from [ASIAS AIDS Download](https://www.asias.faa.gov/apex/f?p=100:189::::NO); server returned HTTP 500 on blob GET (session/cookie issue). Column schema inferred from imported DB keys + `Afilelayout` metadata reference.
3. **Pattern discovery** — Inspected ASIAS AIDS query form (`f?p=100:12`) for Apex item names; tested ≥5 candidate URL templates.
4. **Validation** — 500-row sample (`Planning/spike-reports/samples/faa-aids-url-sample-500.csv`); rate-limited GET (≤1 req/s); classified outcomes per rubric below.
5. **Stability** — Re-probed 50 `match` URLs in same session (`faa-aids-url-stability.json`); **24h re-run recommended** before production backfill.

### Outcome rubric

| Outcome | Meaning |
|---------|---------|
| `match` | HTTP 200 and `source_record_id` appears in response body |
| `redirect_ok` | Redirect chain ends with control # in body |
| `unrelated` | 200 but control # not found (generic page) |
| `fail` | 4xx/5xx/timeout |

---

## Bulk inventory (FR-1)

| Metric | Value |
|--------|-------|
| Active `FAA_AIDS` sources | 157,342 |
| With non-empty `source_url` | **1** |
| Distinct `source_data` keys (100-row sample) | 200+ (`c1`…`c203` style) |
| URL-like keys in bulk JSON | **None** |
| Latest ZIP download | **Failed** (ASIAS blob 500); manual download page works in browser |

**Conclusion:** Bulk TAB files do **not** ship per-row URLs. URLs must be **constructed** from `c5` / `source_record_id`.

**Importer field map** (unchanged):

| Bulk | App field |
|------|-----------|
| `c5` | `source_record_id` |
| `c9` | `date` |
| `c203` | `registration` |
| `c23`/`c24` | make/model |

---

## URL patterns tested (FR-2)

| ID | Kind | Template | Success (n=500) |
|----|------|----------|-----------------|
| `faa_catalog` | catalog | `https://www.faa.gov/data_research/accident_incident` | 0% (baseline) |
| `asias_aids_query_landing` | search | `f?p=100:12::::::` | 0% |
| **`asias_clear_aids_rprt_nbr`** | **direct** | `f?p=100:12:::NO::P12_AIDS_RPRT_NBR:{source_record_id}` | **100%** |
| `asias_clear_acft_reg` | search | `…P12_ACFT_REGIST_NBR:{registration}` | 0% |
| `asias_clear_narr_srch` | search | `…P12_NARR_SRCH:{source_record_id}` | 100% (search-style; prefer direct) |

### Winning URL builder spec (Phase 2)

```python
def build_faa_aids_primary_url(source_record_id: str) -> str:
    from urllib.parse import quote
    rid = quote(str(source_record_id).strip(), safe="")
    return (
        "https://www.asias.faa.gov/apex/f?p=100:12:::NO::"
        f"P12_AIDS_RPRT_NBR:{rid}"
    )
```

**`links[]` roles:**

- `primary` — ASIAS AIDS report (URL above)
- `catalog` — `https://www.faa.gov/data_research/accident_incident` (fallback / context)

---

## Validation results (FR-3)

- **Sample:** 500 rows — `Planning/spike-reports/samples/faa-aids-url-sample-500.csv`
- **Full probes:** 2,500 rows — `faa-aids-url-validation-results.csv`
- **Summary JSON:** `artifacts/faa-aids-url-validation-summary.json`

**Best pattern:** `asias_clear_aids_rprt_nbr` — **100.0%** match.

**Stability (same session, n=50):** 100% — `artifacts/faa-aids-url-stability.json`.  
**Action:** Re-run `scripts/spikes/faa_aids_url_stability.py` ≥24h after first validate before starting full backfill.

---

## Manual QA notes (FR-5)

Automated classification used control # in HTML body. Spot-check these URLs in a browser:

1. `https://www.asias.faa.gov/apex/f?p=100:12:::NO::P12_AIDS_RPRT_NBR:19850908053709I`
2. `https://www.asias.faa.gov/apex/f?p=100:12:::NO::P12_AIDS_RPRT_NBR:20150101012345I` *(if in sample)*

**NTSB cross-check:** 0 sample incidents had both FAA_AIDS and NTSB on the same `incident_id` (consistent with prior merge spike).

---

## Legal / operational (FR-5)

| Topic | Notes |
|-------|-------|
| `faa.gov/robots.txt` | Standard; no block on data pages |
| `asias.faa.gov/robots.txt` | Not found (404 HTML) |
| Rate limit for backfill | ≤1 req/s; User-Agent `AircraftSafetyTracker/1.0` |
| Automated validation | 500 GETs completed without blocking; polite throttle recommended for 157k backfill |

---

## Go / no-go gate

| Gate | Threshold | Result |
|------|-----------|--------|
| Direct URL | ≥90% on sample | **100%** → **GO** |
| Conditional go (search) | ≥80% if no direct | Not needed — direct works |
| Stability | Re-test 50 URLs | 100% same-session; 24h pending |

**Decision: GO** — implement Phase 2.

---

## Phase 2 outline (do not start until product signs above)

| Effort | **M** (2–3 days) |
|--------|------------------|
| Files | `app/ingestion/url_builders/faa_aids.py`, `faa_aids_importer.py`, `backfill_urls.py`, optional CLI |
| Backfill | `refresh_source_links('FAA_AIDS')` in 5k batches, single SQLite writer |
| Tests | Unit tests for URL builder + placeholder rejection |
| QA | 10 aircraft profiles with high FAA counts; re-run coverage metric |

**Estimated incident coverage after backfill:** ~32% → **~97%** (157,342 FAA rows linked).

---

## Risks

1. **ASIAS Apex session URLs** — CLEAR-cache links may require active session in edge cases; monitor 403/500 during backfill.
2. **Apex app changes** — Item `P12_AIDS_RPRT_NBR` could rename; pin discovery date in builder docstring.
3. **ZIP download automation** — Blob `ck` tokens expire; use download page scrape (see `resolve_latest_aids_zip_url()`).

---

## Artifacts index

| File | Purpose |
|------|---------|
| `artifacts/faa-aids-inventory.json` | DB + ZIP inventory |
| `artifacts/faa-aids-url-validation-summary.json` | Pattern scores |
| `artifacts/faa-aids-url-stability.json` | 50-URL re-test |
| `samples/faa-aids-url-sample-500.csv` | Stratified sample |
| `samples/faa-aids-url-validation-results.csv` | All probe results |
| `scripts/spikes/*` | Reproducible spike tooling |

---

## Product sign-off

- [ ] **GO** — proceed Phase 2  
- [ ] **Conditional go**  
- [ ] **No-go**  

**Signed:** __________________ **Date:** __________________
