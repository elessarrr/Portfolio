# NTSB Family Rollup Proposal (0006.3 — Task 5.14)

**Status:** DRAFT skeleton — product review not started  
**Created:** 2026-05-31  
**Source data:** `data/logs/ntsb_enrichment_audit_rows.jsonl` (657 working-link incidents, 279 distinct NTSB `make_model` strings)

---

## What you already reviewed (Task 5.10) — do not repeat

In **May 2026** you signed off that the **657 NTSB records** are good import candidates:

- Details **links work** (docket pages load; no CAROL empty shells)
- **Date, location, operator** look reasonable
- **Make/model** in the export matches NTSB bulk metadata (`cm_vehicles`)

That was: *“Are these real, linkable NTSB incidents we want in the app?”*

---

## What this document is for (Task 5.15) — new question

This review answers a **different** question:

> **Which aircraft page in our catalog should each NTSB string file under?**

Example: NTSB says `BOEING 737-7H4` — we are **not** creating a new empty page for that exact string. We file those incidents on **Boeing 737**, but **each incident keeps its own row** with the exact NTSB make/model stored and shown.

You do **not** need to re-check links or re-read every incident narrative. You **do** need to approve (or override) the **page assignment** for each distinct NTSB string.

---

## Rules for this effort

| Rule | Detail |
|------|--------|
| **Roll up = page only** | Grouping incidents under one aircraft page. Does **not** merge rows or drop data. |
| **657 separate incidents** | Every working-link row becomes its own `Incident` with date, location, operator, fatalities, Details link. |
| **Exact make/model preserved** | Raw NTSB string stored in `IncidentSource.source_data` **and** shown in a new **Make/Model** column on the incident table (0006.3 UI add). |
| **Page names must include Boeing or Airbus** | All aircraft page names (existing or new) must contain `Boeing` or `Airbus` (e.g. `Airbus Helicopters AS350`, not bare `AS350`). |
| **Variant threshold** | ≥ 10 incidents on one NTSB string → prefer keeping variant-level page where catalog already has one; otherwise roll to family page (product override OK). |
| **Stearman** | One page: existing **`Boeing-Stearman Kaydet`** (catalog id **68**). |
| **Helicopters** | Create new pages with `Boeing` or `Airbus` in the name (see Section C). |
| **Generic 737 strings** | Roll to **`Boeing 737`** (new page — not currently in catalog; user approved 2026-05-31). |

---

## How to review

1. **Primary review — Part A (279 strings):** Approve or override which **aircraft page** each NTSB make/model string maps to. Edit `product_decision` / `override_aircraft_page` in the machine-readable file (see below).
2. **Reference only — Part B (657 incidents):** Auto-generated from Part A. Use to spot-check a specific NTSB number if you want — **not a second sign-off gate**.

**Approved mapping (Task 5.16):** [`data/config/ntsb_make_model_to_aircraft.jsonl`](../../data/config/ntsb_make_model_to_aircraft.jsonl) — 279 strings, v1 approved 2026-05-30. Rebuild: `PYTHONPATH=. python scripts/build_ntsb_make_model_mapping.py`.

| File | Rows | Purpose |
|------|------|---------|
| [`data/logs/ntsb_rollup_string_mapping_draft.jsonl`](../../data/logs/ntsb_rollup_string_mapping_draft.jsonl) | **279** | **You review this** — one row per distinct NTSB string |
| [`data/logs/ntsb_rollup_incident_assignments_draft.jsonl`](../../data/logs/ntsb_rollup_incident_assignments_draft.jsonl) | **657** | Auto-derived reference — shows each incident’s proposed page |

Example filter:

```bash
grep -v '^#' data/logs/ntsb_rollup_string_mapping_draft.jsonl | jq 'select(.proposed_aircraft_page=="TBD")'
```

---

## Part A — Executive summary (proposed aircraft pages)

Draft assignments: **279/279 strings mapped** (0 TBD remaining). Regenerate with `PYTHONPATH=. python scripts/export_ntsb_rollup_mapping_draft.py`.

| Proposed aircraft page | NTSB strings | Incidents | Action | Catalog id |
|------------------------|-------------|-----------|--------|------------|
| Boeing 737 | 50 | 159 | create_approved | — (new) |
| Boeing-Stearman Kaydet | 21 | 103 | map_to_existing | 68 |
| Boeing 757-200 | 18 | 56 | map_to_existing | 32 |
| Airbus A320 | 17 | 54 | map_to_existing | 78 |
| Boeing 767-300 | 24 | 46 | map_to_existing | 35 |
| Airbus Helicopters AS350 | 17 | 28 | create_approved | — (new) |
| Boeing 777-200 | 15 | 28 | map_to_existing | 37 |
| Boeing 747-400 | 17 | 25 | map_to_existing | 28 |
| Airbus A330 | 6 | 14 | map_to_existing | — |
| Boeing 717 | 4 | 11 | map_to_existing | 8 |
| Airbus Helicopters (TBD) | 4 | 9 | create_approved | — (new) |
| Boeing 727-200 | 8 | 8 | map_to_existing | 11 |
| Airbus Helicopters EC135 | 5 | 6 | create_approved | — (new) |
| Airbus A300 | 4 | 5 | map_to_existing | — |
| *(others)* | … | … | … | … |

**Product sign-off (Part A):** ☐ Approve summary targets ☐ Overrides noted in JSONL

---

## Part A — Section B: Stearman (21 strings → 103 incidents)

**Proposed page:** `Boeing-Stearman Kaydet` (id **68**) — all strings map here.

| NTSB make_model | Incidents | Proposed page | Your decision |
|-----------------|-----------|---------------|---------------|
| BOEING A75N1(PT17) | 36 | Boeing-Stearman Kaydet | |
| BOEING B75N1 | 18 | Boeing-Stearman Kaydet | |
| BOEING A75N1 | 11 | Boeing-Stearman Kaydet | |
| BOEING E75 | 10 | Boeing-Stearman Kaydet | |
| *(17 more strings)* | 28 | Boeing-Stearman Kaydet | see JSONL |

---

## Part A — Section C: Helicopters (30 strings → 47 incidents)

**Naming rule:** all new pages include `Airbus` or `Boeing`.

| Proposed new page | Example NTSB strings | ~Incidents |
|-------------------|----------------------|------------|
| Airbus Helicopters AS350 | `AIRBUS HELICOPTERS INC AS350B3`, `AIRBUS AS350` | 28 |
| Airbus Helicopters BK117 | `MBB-BK 117 B-2`, `AIRBUS HELICOPTERS MBB-BK 117 C-2` | 4 |
| Airbus Helicopters EC135 | `AIRBUS HELICOPTERS DEUTSCHLAND EC135T3` | 6 |
| Boeing Helicopters H500 | `Boeing Helicopters Div. H500D` | 3 |
| Boeing Helicopters MD600 | `Boeing MD600N` | 2 |
| Airbus Helicopters (TBD) | *(unmatched helicopter strings)* | 9 |

**Product sign-off (helicopters):** ☐ Approve proposed page names ☐ Overrides: ___

---

## Part A — Section D: Boeing 737 family (50 strings → 159 incidents)

**Proposed page:** **`Boeing 737`** (new catalog row — user approved roll-up to family name).

Includes generic and suffix variants, e.g.:

| NTSB make_model | Incidents | Proposed page |
|-----------------|-----------|---------------|
| BOEING 737 | 30 | Boeing 737 |
| Boeing 737 | 15 | Boeing 737 |
| BOEING 737 7H4 | 15 | Boeing 737 |
| BOEING 737-7H4 | 12 | Boeing 737 |
| BOEING 737-8H4 | 9 | Boeing 737 |
| *(45 more strings)* | 78 | Boeing 737 — see JSONL |

Each incident row will still show its **exact** NTSB string in the new Make/Model column.

---

## Part A — Section E: Other fixed-wing families

High-level draft (full list in JSONL):

| Family | Proposed page | ~Incidents |
|--------|---------------|------------|
| 757 | Boeing 757-200 | 56 |
| 767 | Boeing 767-300 | 46 |
| 747 | Boeing 747-400 | 25 |
| 777 | Boeing 777-200 | 28 |
| 727 | Boeing 727-200 | 8 |
| A320 | Airbus A320 | 54 |
| A330 | Airbus A330 | 14 |
| A300 | Airbus A300 | 5 |
| 717 | Boeing 717 | 11 |

---

## Part A — Section F: Product-confirmed edge cases (2026-05-31)

These strings needed manual identification; now resolved:

| NTSB make_model | Incidents | Aircraft page | Action | Notes |
|-----------------|-----------|---------------|--------|-------|
| `AIRBUS F4-622R` | 1 | **Airbus A300-600** (id 73) | map_to_existing | UPS cargo variant; same for `AIRBUS A300 F4-622R` |
| `BOEING MD` | 1 | **Boeing MD-82** | create_approved | Incomplete NTSB string; product confirmed MD-82 (DCA10IA015) |
| `BOEING CV2` | 1 | **Boeing CV2** | create_approved | Boeing cargo vehicle; real model per product review (DCA19CA170) |

---

## Part B — Incident reference (657 rows) — not a re-review

This is **auto-generated** from Part A: each incident inherits its string’s page assignment.

- **File:** `data/logs/ntsb_rollup_incident_assignments_draft.jsonl`
- **Use when:** you want to look up one NTSB number (e.g. `CHI95IA138`) and confirm which page it would land on
- **You do not** need to sign off all 657 lines if Part A is approved

Example row:

```json
{
  "source_record_id": "DFW06LA041",
  "date": "2005-12-26",
  "ntsb_make_model": "Boeing A75N1 (PT17)",
  "proposed_aircraft_page": "Boeing-Stearman Kaydet"
}
```

---

## UI change (0006.3)

Add **Make/Model** column to the incident table (`incident_list.html`):

- **NTSB rows:** show exact NTSB string from `IncidentSource.source_data` / parsed make_model
- **ASN rows:** may show catalog page name or ASN variant if available (TBD in implementation)

Roll-up affects **which page** lists the incident; the column shows **what NTSB recorded** for that event.

---

## Sign-off (Task 5.15)

- [ ] **5.15.1** Part A reviewed — all 279 strings have approved page (**0 TBD**)
- [ ] **5.15.2** Stearman → `Boeing-Stearman Kaydet` (id 68) confirmed
- [ ] **5.15.3** Helicopter page names confirmed (Boeing/Airbus in name)
- [ ] **5.15.4** `Boeing 737` family page approved as new catalog row
- [ ] **5.15.5** Ready to build approved `data/config/ntsb_make_model_to_aircraft.jsonl` (Task 5.16)

**Approved by:** _______________ **Date:** _______________
