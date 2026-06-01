# Exhaustive Local QA — Aircraft Safety Tracker

**Date:** 2026-05-27  
**Target:** `http://127.0.0.1:5003/`  
**Tooling:** gstack `browse` (Playwright headless)  
**Goal:** click through major UX paths; verify **Details** links land on the correct ASN record by comparing **date + operator**.

---

## 1) Setup / environment notes

- **Browse setup work completed** (one-time):
  - `bun`/`bunx` not on PATH in a terminal; used absolute path to run Playwright install.
  - Playwright Chromium binaries were missing; installed:
    - `playwright install chromium`
    - `playwright install chromium-headless-shell`
- **Known dev issues observed during QA (not blocking table/link correctness):**
  - Tailwind CDN warning in console (expected in dev).
  - AI summary regeneration fails due to DeepSeek auth/network problems (see §6).

---

## 2) Pages + routes exercised (clicked through)

- Home: `/`
- Autocomplete/search endpoint (direct navigation):
  - `/search?q=747`
  - `/search?q=A320`
  - `/search?q=737`
  - `/search?q=777`
  - `/search?q=A330`
  - `/search?q=Kenya%20Airways` (negative test)
- Aircraft detail pages:
  - Boeing 747-100: `/aircraft/25`
  - Airbus A320: `/aircraft/78`
  - Boeing 737-800: `/aircraft/23`
  - Boeing 777-200: `/aircraft/37`
  - Airbus A330-200: `/aircraft/82`
- Feedback form:
  - `/feedback/request`

---

## 3) Incident filters (All / Fatal / Non-Fatal)

### Boeing 747-100 (`/aircraft/25`)

- **All incidents:** mixed rows (0 fatalities and >0 fatalities)
- **Fatal Only:** rows include fatalities > 0 (e.g., 230, 9, 259…)
- **Non-Fatal Only:** rows show fatalities = 0

✅ **Result:** filter works and updates content.

### Airbus A320 (`/aircraft/78`)

- Aircraft page shows **Fatal Incidents = 0**
- **Fatal Only** filter renders “No incidents found matching criteria.”

✅ **Result:** filter works; empty state shown correctly.

### Boeing 737-800 (`/aircraft/23`)

- **Fatal Only** filter shows exactly 2 fatal rows (fatalities 114, 154)
- **Non-Fatal Only** filter shows only 0-fatality rows

✅ **Result:** filter works and aligns with summary counts.

---

## 4) Details-link verification (date + operator cross-check)

Method for each row:
1. Record internal row **Date** + **Operator**
2. Capture the `Details ↗` link `href` (ASN wikibase URL)
3. Open ASN page and confirm:
   - `Date:` matches day/month/year
   - `Owner/operator:` matches operator string

### A) Boeing 747-100 (`/aircraft/25`)

**All incidents:**

- Internal: `1996-07-17` / `Trans World Airlines - TWA`  
  ASN: `https://aviation-safety.net/wikibase/324416`  
  Verified: `Date: Wednesday 17 July 1996`, `Owner/operator: Trans World Airlines - TWA` ✅

- Internal: `1996-06-17` / `Tower Air`  
  ASN: `https://aviation-safety.net/wikibase/357214`  
  Verified: `Date: Monday 17 June 1996`, `Owner/operator: Tower Air` ✅

- Internal: `1996-06-15` / `Corsair`  
  ASN: `https://aviation-safety.net/wikibase/488196`  
  Verified: `Date: Saturday 15 June 1996`, `Owner/operator: Corsair` ✅

**Fatal-only (additional spot-check):**

- Internal: `1989-02-24` / `United Airlines`  
  ASN: `https://aviation-safety.net/wikibase/326360`  
  Verified: `Date: Friday 24 February 1989`, `Owner/operator: United Airlines` ✅

### B) Airbus A320 (`/aircraft/78`)

- Internal: `2001-04-19` / `America West Airlines`  
  ASN: `https://aviation-safety.net/wikibase/370498`  
  Verified: `Date: Thursday 19 April 2001`, `Owner/operator: America West Airlines` ✅

- Internal: `2001-04-12` / `Air Canada`  
  ASN: `https://aviation-safety.net/wikibase/89826`  
  Verified: `Date: Thursday 12 April 2001`, `Owner/operator: Air Canada` ✅

### C) Boeing 737-800 (`/aircraft/23`)

**Non-fatal (baseline):**

- Internal: `2008-04-29` / `Ryanair`  
  ASN: `https://aviation-safety.net/wikibase/17639`  
  Verified: `Date: Tuesday 29 April 2008`, `Owner/operator: Ryanair` ✅

**Fatal-only (additional spot-check):**

- Internal: `2007-05-05` / `Kenya Airways`  
  ASN: `https://aviation-safety.net/wikibase/321963`  
  Verified: `Date: Saturday 5 May 2007`, `Owner/operator: Kenya Airways` ✅

### D) Boeing 777-200 (`/aircraft/37`)

- Internal: `2010-04-25` / `Emirates`  
  ASN: `https://aviation-safety.net/wikibase/74068`  
  Verified: `Date: Sunday 25 April 2010`, `Owner/operator: Emirates` ✅

### E) Airbus A330-200 (`/aircraft/82`)

- Internal: `2014-03-18` / `Fiji Airways`  
  ASN: `https://aviation-safety.net/wikibase/388567`  
  Verified: `Date: Tuesday 18 March 2014`, `Owner/operator: Fiji Airways` ✅

- Internal: `2014-02-09` / `Royal Air Force - RAF`  
  ASN: `https://aviation-safety.net/wikibase/163810`  
  Verified: `Date: Sunday 9 February 2014`, `Owner/operator: Royal Air Force - RAF` ✅

**Summary:** 10/10 spot checks matched (no mismatches found).

---

## 5) “Search for multiple airlines” note

Tried searching by airline/operator name:

- `/search?q=Kenya%20Airways` → “No aircraft found matching \"Kenya Airways\"”
- Home search box filled with “Air Canada” did not show results on the home page (the rendered UI is aircraft-model search only).

**Interpretation:** current UX search is aircraft-centric, not airline/operator-centric (expected given the placeholder copy + endpoint behavior).

---

## 6) Issues observed (non-blocking to link correctness)

### A) Tailwind CDN warning

- Console warning repeats:
  - `cdn.tailwindcss.com should not be used in production...`
- Network shows Tailwind loaded from CDN and HTMX from unpkg.

**Impact:** none in dev; but should be addressed for production polish.

### B) AI summary regenerate failures

On multiple aircraft pages, “Regenerate” shows user-visible errors like:

- `Authentication Fails, Your api key ... is invalid` (401)
- Prior sessions also showed `httpx.ProxyError: 403 Forbidden` leading to `openai.APIConnectionError: Connection error`

**Impact:** summary generation is unreliable and error copy is shown inline; page still renders and incident table works.

---

## 7) Recommendations / follow-ups

- **P0 (UX):** Hide raw DeepSeek error payloads from end users; show a generic failure message with a retry hint.
- **P1 (Prod readiness):** Bundle Tailwind locally (or pin a build pipeline) rather than using Tailwind CDN.
- **P2 (Product clarity):** If users will search by airline/operator, add a separate operator search feature; current `/search` is aircraft-only.

---

## Addendum A — requested wide “Details” link checks (20 Boeing + 20 Airbus, 5 each)

### What I attempted

- **Sampling**: selected **20 Boeing** aircraft and **20 Airbus** aircraft from `data/aircraft_safety_v3.db`, restricted to aircraft with **≥ 5 incidents** having a non-empty `asn_url` and non-empty `operator`. Then selected **5 random incidents per aircraft** (total **200** incident URLs).
- **Verification target** (same as the earlier spot-check method): for each incident, confirm the ASN page’s **Date** + **Owner/operator (or Operator)** matches our DB’s `incident.date` + `incident.operator`.

### Blocker encountered

I can reliably open ASN pages via **gstack `browse`** interactively (as used above). However, my attempt to automate all 200 validations via a standalone Playwright harness produced many cases where the loaded content did not contain parseable `Date` / `Owner/operator` fields (consistent with anti-bot / headless-detection differences).

### Artifacts (so we can resume cleanly)

- **200-URL checkset (generated)**: `/Users/Bhavesh/.cursor/projects/Users-Bhavesh-Documents-GitHub-Portfolio-Aircraft-Safety-Tracker/agent-tools/b53ba9d7-46f1-4ea0-b822-28fd7375d873.txt`
- **Latest automated run output** (per-incident extracted fields + status): `/Users/Bhavesh/.cursor/projects/Users-Bhavesh-Documents-GitHub-Portfolio-Aircraft-Safety-Tracker/agent-tools/c5d20e5f-0f9e-42fa-ba55-71c2e22a73f2.txt`

### Recommended next move (to actually complete the 200/200 verification)

- Re-run the wide checks using **gstack `browse` itself** (same stack that succeeded in the earlier “10/10” checks), in **small batches** (10–20 URLs per batch) to keep logs small and to extract `Date` + `Owner/operator` directly from the DOM.

### Completed run (2026-05-28) — gstack `browse` throttled verifier

- **Approach:** ran a single-threaded verifier using the gstack `browse` binary with pacing (per-URL delay + per-model cooldown) to avoid ASN headless/anti-bot issues.
- **Verifier script:** `scripts/verify_asn_checkset.py`
- **Output artifact (latest):** `/Users/Bhavesh/.cursor/projects/Users-Bhavesh-Documents-GitHub-Portfolio-Aircraft-Safety-Tracker/agent-tools/asn_200_verification_gstack_browse.results.v2.json`
- **Result:** **194/200 PASS (strict match)**, with **6 exceptions**:
  - **1 dead ASN URL (404):** `incident_id=4333` (`https://aviation-safety.net/wikibase/197625`)
  - **1 partial ASN date:** `incident_id=4871` shows `Date:xx Jan 2003` (operator matches; day missing on ASN)
  - **4 operator label mismatches (likely aliases / multi-party event):**
    - `incident_id=4169`: DB `FedEx Express` vs ASN `FedEx`
    - `incident_id=4342`: DB `SATA Internacional` vs ASN `Azores Airlines`
    - `incident_id=5067`: DB `Condor Flugdienst` vs ASN `Condor`
    - `incident_id=5069`: ASN includes both `Delta Air Lines` and `Air France` (ground collision event; DB stores only Delta)
- **Replacement candidate for the 404 (to keep the “200 checked” effort complete):**
  - Airbus A310 (same `aircraft_id=75`): `incident_id=4244` → `https://aviation-safety.net/wikibase/372689` (200 OK; has parseable Date + Owner/operator)

---

## QA skill review

Ran the repository’s `/qa` workflow against `http://127.0.0.1:5003/` using gstack `browse` (Playwright) and captured evidence screenshots.

### Pages exercised (via `browse`)

- Home: `/`
- Aircraft pages:
  - `/aircraft/25` (Boeing 747-100)
  - `/aircraft/78` (Airbus A320)
  - `/aircraft/23` (Boeing 737-800)
  - `/aircraft/37` (Boeing 777-200)
  - `/aircraft/82` (Airbus A330-200)
- Feedback form: `/feedback/request`
- Mobile viewport smoke: home at `375x812`

### Evidence artifacts (screenshots)

All screenshots are under `.gstack/qa-reports/screenshots/`:

- `qa-initial.png`
- `aircraft-25.png`, `aircraft-78.png`, `aircraft-23.png`, `aircraft-37.png`, `aircraft-82.png`
- Filter interaction evidence:
  - `aircraft-78-filter-before.png`, `aircraft-78-filter-after.png`, `aircraft-78-filter-after-diff.png`
  - `aircraft-23-filter-before.png`, `aircraft-23-filter-after.png`, `aircraft-23-filter-after-diff.png`
- Feedback form evidence:
  - `feedback-request-before.png`, `feedback-request-after.png`
- Mobile:
  - `home-mobile-375x812.png`

### Findings

#### ISSUE-001 — Tailwind CDN warning in console (Low)

- **Repro**: load `/` or any `/aircraft/<id>` page, then check console.
- **Observed**: warning repeats: `cdn.tailwindcss.com should not be used in production...`
- **Impact**: none in local dev, but should be removed for production polish.
- **Evidence**: any of the captured page screenshots above (warning observed across pages).

#### ISSUE-002 — Empty submit on “Request Missing Data” shows no visible validation (Medium)

- **Repro**:
  - Go to `/feedback/request`
  - Leave both fields empty
  - Click **Request Data**
- **Observed**: page remains on `/feedback/request` with no visible validation error messaging / state change.
- **Impact**: users can’t tell why submission didn’t work (or whether it succeeded).
- **Evidence**: `feedback-request-before.png` → `feedback-request-after.png`

