# Engineering Log & Knowledge Journal

## May 2026

- **2026-05-24**: **PRD 0004 — Taxonomy rollup shipped on v2 (Phase 1).**
  - *Schema:* `aircraft_family_member` table + 751 explicit Boeing/Airbus family→variant mappings in `data/aircraft_family_members.csv`.
  - *Query rollup:* Family pages aggregate incidents from mapped member profiles (no `incident.aircraft_id` migration).
  - *Hero results:* `/aircraft/88` (737-300) **50 → 676** incidents, **0 → 566** FAA ASIAS links; `/aircraft/70` (747) FAA **7 → 439**; search `7373` → canonical id 88.
  - *CLI:* `flask import-data seed-family-rules [--dry-run] [--regenerate-csv]`.
  - *Phase 2 deferred:* ~remaining unmapped Boeing/Airbus FAA variant pages (see task 9.0).
  - *Branch policy:* `main` untouched.

- **2026-05-24**: **PRD 0003 — Boeing/Airbus FAA profile attach shipped on v2.**
  - *Module:* `app/ingestion/linking/faa_profile_attach.py` + CLI `flask import-data attach-faa-boeing-airbus`.
  - *Live run:* **5,877** orphan FAA Boeing/Airbus incidents attached via `resolve_aircraft()`; **0** exact date+reg merges (as dry-run predicted).
  - *Coverage:* Boeing profile link rate **54.7% → 81.9%**; Airbus **85.1% → 88.0%**; **492** Boeing models now have ≥1 FAA-linked profile incident.
  - *Spot-check:* `/aircraft/840` (Boeing 727232) — **174/174** incidents show ASIAS **Details ↗** links. `/aircraft/70` (747) — 19/106 linked (7 FAA); remainder mostly foreign-led NTSB no-link (unchanged).
  - *Branch policy:* `main` untouched. Exact match only — no fuzzy merge.

- **2026-05-24**: **Link Enrichment v1 shipped on v2 (PRD 0002).**
  - *Commits:* `9342bd8` (baseline link helpers + spike scripts), `82abece` (FAA ASIAS URL builder + backfill support).
  - *Backfill:* `refresh_source_links('FAA_AIDS')` — **157,342/157,342** rows updated in ~25 min. DB lock during run was expected (single writer).
  - *Coverage:* FAA URLs 1 → 157,342; incident-level active URL **32% → 97.0%** (234,663 / 241,802).
  - *UX:* Bishkek DCA17RA058 — no dead CAROL/docket links; foreign-led FAQ on `/aircraft/70`. FAA ASIAS verified on `/aircraft/55` and `resolve_source_href`.
  - *Branch policy:* `main` untouched (portfolio). Freeze link work ≥1 week.
  - *Deferred:* `global_incident_list.html`, in-app narrative, CLI backfill command, v2→main cutover.

- **2026-05-23**: Fixed nested repository Git bugs.
  - *Prompt*: User requested a fix for terminal syntax errors and detached branch UI in Cursor.
  - *Action*: Fixed broken repository origin mapping, sanitized parenthesis syntax with single quotes, and enabled `git.openRepositoryInParentFolders` in Cursor user settings.
  - *Outcome*: Workspace safely targets the `v2-(first-round-of-feedback-from-RJ)` branch from the `Aircraft Safety Tracker` sub-folder.

---

### 2026-05-23 — Multi-source link enrichment, FAA AIDS URL spike (GO), Boeing 747 link UX, foreign-led NTSB fix

**Branch:** `v2-(first-round-of-feedback-from-RJ)` (uncommitted changes at session end)  
**App:** Flask dev server on `http://127.0.0.1:5001` (`run.py`) — restart required after code changes  
**DB:** `data/aircraft_safety.db` (~2.6 GB, ~242k incidents)

#### 1. WHAT WE COMPLETED

**Link enrichment & ingestion (prior + this session)**
- ASN backfill: **1796/1796** URLs applied.
- NTSB `links[]` refresh run in batches (~75k active rows updated).
- Exact FAA↔NTSB merge dry-run: **0 pairs** (no automatic merge path).
- Fuzzy merge assessed as not worth full run.

**FAA AIDS per-record URL spike (PRD 0001) — decision: GO**
- **PRD:** `Planning/tasks/0001-prd-faa-aids-per-record-url-spike.md`
- **Tasks:** `Planning/tasks/tasks-0001-prd-faa-aids-per-record-url-spike.md` (tasks 1.0–6.0 done; **6.6 product sign-off pending**)
- **Report:** `Planning/spike-reports/0001-faa-aids-url-spike-report.md`
- **Winning URL pattern (100% on 500-row sample):**
  `https://www.asias.faa.gov/apex/f?p=100:12:::NO::P12_AIDS_RPRT_NBR:{source_record_id}`
  where `source_record_id` = bulk field `c5`.
- **Spike scripts created:**
  - `scripts/spikes/faa_aids_spike_lib.py` — URL patterns, HTTP probe, ASIAS resolver
  - `scripts/spikes/faa_aids_url_inventory.py` — FR-1 DB field inventory
  - `scripts/spikes/faa_aids_export_sample.py` — stratified 500-row sample export
  - `scripts/spikes/faa_aids_url_validate.py` — automated validation (2,500 probes)
  - `scripts/spikes/faa_aids_url_stability.py` — same-session stability re-test
  - `scripts/spikes/README.md`, `scripts/__init__.py`
- **Artifacts:** `Planning/spike-reports/artifacts/`, `Planning/spike-reports/samples/`
- **`.env.example`** — documented optional `FAA_AIDS_ZIP_URL_TEMPLATE`
- **Phase 2 NOT implemented** (builder + ~157k backfill) — blocked until product signs spike report.

**Boeing 707 / general incident link UX fixes**
- **`app/link_helpers.py`** — central URL resolution: `resolve_source_href`, `resolve_source_hrefs`, `resolve_ntsb_href`, `pick_primary_source`, `resolve_primary_href`, `incident_has_active_link`; integrates `app/ingestion/url_builders/*` and `link_schema`.
- **`app/__init__.py`** — registers Jinja globals for link helpers (+ foreign-led helpers, see below).
- **`app/templates/components/incident_list.html`** — uses link helpers instead of hard-coded NTSB docket URLs; shows CAROL for inactive WA-only rows when linkable; FAQ copy for preliminary records.
- **`app/ingestion/url_builders/ntsb.py`** — added `carol_detail_has_public_content()`; only emit CAROL/docket when narrative/report metadata suggests public web content; skip WA docket when no public content.
- **`app/routes.py`** — debug instrumentation added then **removed** after verification.
- Removed two test DB rows with `example.com` placeholder URLs (incidents 1786, 1787).
- **`tests/test_link_helpers.py`** — 8 tests, **all passing**.

**Boeing 747 / Bishkek foreign-led NTSB fix (last work in session)**
- **User report:** DCA17RA058 (Bishkek 2017, `incident_id=198660`, `cm_mkey=94608`) — both CAROL (`carol.ntsb.gov/investigations/detail/94608`) and docket (`data.ntsb.gov/Docket/?NTSBNumber=DCA17RA058`) render **empty pages** (screenshots confirmed).
- **Root cause:** `cm_agency: "Other"` = NTSB accredited rep only (Kyrgyzstan leads). Bulk data has `factualNarrative` (~410 chars) but **no public CAROL/docket content** on ntsb.gov. Prior logic wrongly treated DB narrative as proof of linkable CAROL page.
- **Files modified:**
  - `app/ingestion/url_builders/ntsb.py` — `carol_detail_has_public_content()` returns `False` when `cm_agency == "OTHER"`; `build_ntsb_links()` skips docket for `foreign_led` cases (lines ~12–16, ~80–86).
  - `app/link_helpers.py` — added `is_foreign_led_ntsb()`, `incident_has_foreign_led_ntsb()`.
  - `app/__init__.py` — exposes new Jinja globals.
  - `app/templates/components/incident_list.html` — shows "Foreign-led investigation (NTSB accredited rep only)" + FAQ link when no outbound URL (~line 123).
  - `tests/test_link_helpers.py` — `test_resolve_ntsb_skips_foreign_led_even_with_narrative()` for DCA17RA058; updated narrative test to use `cm_agency: "NTSB"`.
- **Verified:** `resolve_ntsb_href` / `resolve_source_href` / `resolve_source_hrefs` all return `None`/`[]` for DCA17RA058 after fix.

**Tests passed this session**
- `tests/test_link_helpers.py` — **8/8 pass**
- Broader run `tests/test_link_helpers.py tests/test_source_links.py` — **14 pass, 2 fail** (pre-existing/unrelated to foreign-led fix):
  - `test_aircraft_incident_list_renders_media_source_with_generic_link_style` — expects "MEDIA" label text; template shows "Press ↗"
  - `test_aircraft_incident_list_shows_wa_faq_note_for_inactive_ntsb_only` — uses `WPR24LA123` (not WA-coded); FAQ branch not triggered

#### 2. CURRENT ROADBLOCKS & STATE

| Area | State |
|------|--------|
| **Uncommitted code** | `app/__init__.py`, `app/ingestion/url_builders/ntsb.py`, `app/link_helpers.py`, `app/templates/components/incident_list.html`, `tests/test_link_helpers.py` (+ spike scripts, Planning docs, `.env.example`) — **not committed** |
| **FAA Phase 2** | Spike **GO** but **blocked on product sign-off** (task 6.6). ~157,342 FAA_AIDS rows still have no URL; coverage stuck at ~32%. |
| **Bishkek / foreign-led** | **Fixed in code** — no dead CAROL/docket links for `cm_agency=Other` (~393 NTSB rows). User must **restart Flask** and hard-reload aircraft page to see change. |
| **In-app narrative** | User asked (optional) whether to surface stored `factualNarrative` in-app for foreign-led cases — **not implemented**. |
| **`global_incident_list.html`** | Still uses raw `source.source_url` — **not updated** to match `incident_list.html` link helper pattern. |
| **Flask CLI** | `flask import-data backfill-source-urls`, `link-coverage-report` modules exist but **not wired** in `app/ingestion/cli.py`. |
| **Stale tests** | 2 failures in `tests/test_source_links.py` (see above). |
| **24h stability** | Spike recommends re-run `scripts/spikes/faa_aids_url_stability.py` ≥24h before production FAA backfill. |
| **SQLite locks** | Only one writer at a time against `data/aircraft_safety.db`. |

**Code we were looking at at session end:** `app/ingestion/url_builders/ntsb.py` lines 9–24 (`carol_detail_has_public_content`) and `app/templates/components/incident_list.html` lines 104–130 (primary link + foreign-led FAQ branch).

#### 3. NEXT IMMEDIATE STEPS

1. **Product sign-off on spike report** (`Planning/spike-reports/0001-faa-aids-url-spike-report.md`) → implement Phase 2: update `app/ingestion/url_builders/faa_aids.py` with ASIAS direct URL, wire import + `backfill-source-urls` CLI, batch backfill ~157k FAA_AIDS rows (expected coverage ~32% → ~97%). Re-run 24h stability script first if ≥24h has elapsed since validate run.
2. **Restart app + verify Boeing 747 Bishkek row** (`/aircraft/70`) shows "No external link" + foreign-led FAQ (not CAROL/docket). Optionally implement **in-app narrative display** for `cm_agency=Other` rows that have `factualNarrative` in `source_data` but no public URL.
3. **Align `global_incident_list.html`** with `incident_list.html` link helpers; fix or update the 2 failing `tests/test_source_links.py` cases to match current template behavior.

#### 4. KEY DISCOVERIES

- **FAA AIDS bulk has no URL columns** — only `c5`/`source_record_id` can build links; ASIAS Apex `P12_AIDS_RPRT_NBR` is 100% match on sample.
- **~157,342 FAA_AIDS** active sources; **1** had URL at spike start → largest coverage gap in the product.
- **Incident-level link coverage ~32%** before FAA backfill; ~68% of incidents lack any active resolvable URL.
- **NTSB CAROL is a JS SPA** — HTTP 200 often returns ~1.9 KB empty shell; `scripts/validate_incident_links.py` skips CAROL HTTP validation for this reason.
- **`factualNarrative` in bulk JSON ≠ public CAROL page** — especially for accredited-rep cases (`cm_agency: "Other"`, ~393 rows, ~220 with narrative text).
- **Bishkek DCA17RA058:** `cm_agency=Other`, `cm_reportType=None`, no docket released; narrative exists only in imported bulk data.
- **Boeing 747 (`aircraft_id=70`):** 99 incidents, UI shows 50 (`limit(50)`); top 50 dominated by inactive WA NTSB (~47) with CAROL URLs in DB but often empty public pages.
- **747 link bug was template + resolver**, not missing DB data — `incident_list.html` previously hard-coded docket URL before stored CAROL URL.
- **Exact FAA↔NTSB merge: 0 pairs** — no automatic cross-source linking via record ID overlap.
- **ASIAS ZIP blob download** often HTTP 500 from automation; spike used DB inventory + browser-derived blob URL pattern instead.

**Coverage reference (DB at session time)**

| Source | Active rows | With URL |
|--------|-------------|----------|
| NTSB | ~75k | Most have CAROL/docket in DB |
| FAA_AIDS | 157,342 | 1 |
| ASN | ~1.8k | Backfilled |

**Winning FAA URL builder (Phase 2 spec — not yet in app code):**

```python
def build_faa_aids_primary_url(source_record_id: str) -> str:
    from urllib.parse import quote
    rid = quote(str(source_record_id).strip(), safe="")
    return (
        "https://www.asias.faa.gov/apex/f?p=100:12:::NO::"
        f"P12_AIDS_RPRT_NBR:{rid}"
    )
```

