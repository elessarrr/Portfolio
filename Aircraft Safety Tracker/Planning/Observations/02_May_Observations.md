# Outstanding Issues and Open Items

**Date:** May 02, 2026  
**Status:** Active Single Source of Truth for Project Stakeholders  

---

## Table of Contents
1. [Production `ev_id` Mapping Data](#1-production-ev_id-mapping-data)
2. [Phase 2.4 NTSB Records Verification](#2-phase-24-ntsb-records-verification)
3. [Validation Script Environment Issue](#3-validation-script-environment-issue)
4. [Additional Open Items & Technical Debt](#4-additional-open-items--technical-debt)

---

## 1. Production `ev_id` Mapping Data

**Status:** 🔴 Blocked / Pending Data Engineering  
**Priority:** High  
**Owner:** Data Engineering / Backend Team  
**Target Deployment:** TBD (Pending data acquisition)

### Overview
To finalize the NTSB URL remediation (PRD-0019 Phase 2), we must map legacy NTSB accident numbers (e.g., `DCA88WA057`) to their corresponding internal CAROL `ev_id` or legacy MKey. The remediation script (`scripts/remediate_ntsb_legacy_source_urls.py`) is fully built and tested but currently runs against an empty scaffold mapping file, resulting in 0 updates.

### Requirements & Constraints
*   **Data Sources:** Requires a bulk data export from the NTSB Aviation Accident Database (typically distributed as a Microsoft Access `.mdb` file or via a specialized API export) containing the crosswalk between `AccidentNumber` and `ev_id`.
*   **Validation Requirements:** The mapping file must be formatted as a JSON/CSV dictionary. Prior to applying to production, a `--dry-run` of the remediation script must be executed to verify match rates and ensure no unintended URL malformations occur.
*   **Blocking Dependencies:** Phase 2.4 (Manual Verification) cannot commence until this mapping data is acquired and applied to the production database.

---

## 2. Phase 2.4 NTSB Records Verification

**Status:** ⏸️ Pending (Blocked by Section 1)  
**Priority:** High  
**Owner:** QA / Product Team  
**Due Date:** +2 Days after `ev_id` mapping deployment

### Verification Process
Once the production `ev_id` mapping data is applied, a mandatory manual QA pass must be executed against a sample of 50 remediated NTSB records. 

*   **Reference Document:** The formal runbook is located at `Planning/tasks/phase-2.4-ntsb-manual-verification-checklist.md`.
*   **Verification Criteria:**
    1.  The URL in `IncidentSource.source_url` or `report_url` successfully resolves (HTTP 200).
    2.  The resulting page is a valid NTSB investigation report or CAROL docket page.
    3.  The content matches the specific aircraft, date, and location of the incident record.
    4.  If a PDF link is provided, it downloads without corruption or "MKey 0" JSON error payloads.
*   **Assigned Personnel:** QA Lead (with Product Manager sign-off).
*   **Documentation Requirements:** The QA engineer must record the 50 sampled IDs, their previous URLs, new URLs, and a boolean Pass/Fail status in a dedicated validation spreadsheet. Any failures require an immediate halt to further deployments and a rollback of the URL remediation script.

---

## 3. Validation Script Environment Issue

**Status:** ✅ Resolved (Historical Documentation)  
**Priority:** Critical (Completed)  
**Owner:** Backend Engineering  

### Comprehensive Problem Description & Root Cause Analysis
During the implementation of Phase 6 (NTSB "WA" Docket Suppression), the weekly link validation script (`scripts/validate_incident_links.py`) failed to properly process records in the development environment.
*   **Broad Skip Logic:** The Phase 5 fix instructed the script to skip NTSB `source_url` validation to prevent CAROL false positives (HTTP 200 on missing data). However, this logic was too broad and skipped *all* NTSB URLs, including the newly introduced `data.ntsb.gov/Docket/` URLs that explicitly needed validation.
*   **Missing Inactivation Logic:** The script correctly set `source_url = None` for broken links, but failed to update the `is_active = False` flag. Without this flag, the UI templates continued to render dead links.
*   **Environment Constraints:** Running the script iteratively processed thousands of records, making external HTTP calls that were slow and prone to rate-limiting, making local dev testing nearly impossible without a targeted mode.

### Implemented Solutions & Technical Specifications
1.  **Targeted Skip Logic:** Modified `_validate_primary_source_url()` to only skip validation if the URL specifically contains `carol.ntsb.gov`. Docket URLs (`data.ntsb.gov/Docket/`) are now actively routed to `validate_source_url()`.
2.  **Database State Mutation:** Updated the `validate_and_update()` commit block to explicitly set `source.is_active = False` when a link evaluates as `"broken"`, and `True` when `"valid"` or `"updated"`.
3.  **Targeted Testing CLI:** Added an `--id <id>` argument to the argparse configuration, allowing developers to target a specific `IncidentSource` ID and bypass the bulk iterator.

### Testing Status & Procedures
*   **Status:** ✅ Completed end-to-end.
*   **Testing Procedures Executed:**
    1.  **Unit Tests:** Executed `pytest tests/test_validate_incident_links.py`. All 14 tests passed, confirming source-aware logic routing.
    2.  **Live Targeted Run:** Temporarily injected a WA docket URL into `IncidentSource` ID 52. Ran `python scripts/validate_incident_links.py --id 52`. Confirmed the script executed a GET request, parsed the "has not been released" message, and successfully updated the DB state to `is_active = False`.
    3.  **UI Suppression Verification:** Rendered `global_incident_list.html` programmatically against the updated ID 52 record. Confirmed the Jinja template correctly suppressed the NTSB badge based on the `is_active` flag.

### Remaining Open Items
*   **Priority:** Low
*   **Item:** Monitor the cron job output after the first production run to ensure rate limiting (`DOMAIN_DELAY`) holds up against bulk NTSB docket requests.

---

## 4. Additional Open Items & Technical Debt

The following items represent known issues and technical debt that fall outside the immediate scope of PRD-0019 but require tracking for upcoming sprints.

| Category | Item Description | Owner | Priority | Status | Target / Due Date |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Testing / CI** | **Google Generative AI Dependency:** `test_gemini.py` is failing locally because the `google-generativeai` package is not installed in the environment. | DevOps | Medium | 🟡 Open | Next Sprint |
| **Database / Schema** | **Drop Legacy `asn_url` Column:** Following the successful migration to the `IncidentSource` table (Phase 3), the legacy `Incident.asn_url` column was made nullable. A deferred migration stub (`c955648fb8e6`) exists to drop this column entirely. | Backend | Low | 🟡 Open | v2.1 Release |
| **Data Quality** | **Missing Report URLs for NTSB:** Several older NTSB records lack a `report_url`. We currently stamp these as validated without mutating them. A future data ingestion pass is needed to backfill these reports. | Data Eng | Low | 🟡 Open | Backlog |
| **Monitoring** | **Link Break Alerts:** The `LINK_BREAK_ALERT_ENABLED` environment variable is currently inactive. We need to wire this up to Slack/Email notifications to proactively catch documentation drift. | DevOps | Medium | 🟡 Open | Next Sprint |

---
*Document maintained by the Engineering Team. Please update statuses and add new items as they are discovered.*