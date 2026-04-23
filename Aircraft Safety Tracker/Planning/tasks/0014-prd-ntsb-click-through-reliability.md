# 0014-prd-ntsb-click-through-reliability

## 1. Introduction/Overview

Users click an NTSB source link on an incident row and sometimes see a browser error (e.g., `net::ERR_ABORTED`) instead of landing on a usable NTSB page with more incident details. This is happening in both normal browsers and embedded preview/iframe environments.

This PRD defines a reliability-focused change set so clicking NTSB links consistently takes the user to a working NTSB web page with more incident information. This PRD is intentionally scoped to NTSB only; once resolved, we will apply the same approach to other sources (ASN, FAA_AIDS, FAA_SDR).

## 2. Goals

1. Ensure the UI exposes a reliable NTSB click-through experience that opens a working NTSB web page containing additional incident information.
2. Preserve and expose both NTSB link types when available (e.g., investigation detail and docket/documents), rather than choosing one and hiding the other.
3. Make NTSB links behave consistently across environments (local browser and embedded preview/iframe).

## 3. User Stories

- As a user, when I click the NTSB link on an incident, I want to be taken to an NTSB web page where I can learn more about that incident.
- As a user, I want to see both the NTSB investigation detail link and any related docket/documents link (if available), so I can choose the most useful destination.

## 4. Functional Requirements

1. The incident list UI must display NTSB links as explicit link(s) when the incident has an NTSB source.
2. If both an NTSB investigation detail link and an NTSB docket/documents link are available for an incident, the UI must display both links (two separate actions).
3. NTSB links must open in a way that works in both normal browsing and embedded/preview contexts:
   1. External links must open in a new tab/window using `target=\"_blank\"`.
   2. External links must include `rel=\"noopener noreferrer\"`.
4. The system must standardize the NTSB “investigation detail” URL format used in the application:
   1. If the currently stored NTSB URL pattern is not reliably navigable in-browser, the system must generate and store a more stable NTSB web URL based on available identifiers.
   2. The system must not degrade the user experience by sending users only to a PDF as the primary click-through.
5. The ingestion layer must store both NTSB link types when they exist:
   1. `IncidentSource.source_url` should represent an NTSB web “investigation detail” destination.
   2. `IncidentSource.report_url` should represent an alternate NTSB destination (often a docket/document/report link). This may be a PDF; it should still be stored and made available as the secondary link when present.
6. The incident list UI must label the NTSB links clearly so the user understands what each link is:
   1. Example labels: “NTSB Details” and “NTSB Docs”.
7. The system must not silently rewrite existing links without traceability:
   1. Any migration/backfill that changes stored NTSB URLs must be repeatable and idempotent.
   2. Any record that cannot be mapped to a more stable NTSB URL should retain its original URL.

## 5. Non-Goals (Out of Scope)

- Implementing reliability changes for ASN, FAA_AIDS, or FAA_SDR links (explicitly deferred to the next PRD after NTSB is stable).
- Adding “Copy link” buttons, user-facing fallback hints, or additional UI affordances for failed navigation (explicitly deferred per product decision).
- Attempting to guarantee NTSB external-site uptime or fix issues inside NTSB’s site (we only control our URLs and link behavior).

## 6. Design Considerations (Optional)

- The incident list row should not become visually noisy. Prefer compact link chips/buttons consistent with existing source badge styling.
- When both links exist, keep them adjacent and clearly labeled to avoid confusion.

## 7. Technical Considerations (Optional)

### 7.1 Likely Root Cause Categories

Based on observed behavior and initial checks, the most likely causes are:

1. **External SPA navigation + embedded contexts:** CAROL pages are SPA-driven and may behave differently under preview/iframe/popup-restricted contexts, leading to aborted navigations.
2. **URL format drift:** The “carol.ntsb.gov/investigations/detail/{id}” format may not be the best current canonical destination for the new/enhanced CAROL experience.

### 7.2 Candidate “Stable” NTSB Web Destinations

Implementation should choose the most stable web destination format based on which identifiers are available in the NTSB payload (examples):

- A canonical CAROL “investigation detail” route if one exists and is navigable in a normal browser.
- A CAROL search/deeplink URL on `data.ntsb.gov/carol-main-public/` that reliably resolves to a result view in-browser.

The implementation should prefer a destination that:

- Is a web page (not a PDF) for the primary “NTSB Details” link.
- Works in both standard browsing and embedded/preview contexts when opened in a new tab.

### 7.3 Expected Code Touch Points (For Engineering)

- Ingestion URL construction:
  - `app/ingestion/importers/ntsb_importer.py` (construct/store NTSB URLs)
- Link rendering and selection:
  - `app/templates/components/incident_list.html` (render both NTSB links when present; enforce external-link attributes)
  - Any helper used to select primary/secondary links for a source badge
- Optional repeatable data migration/backfill:
  - A script in `scripts/` to update existing NTSB `IncidentSource` rows to the stabilized URL format (idempotent)
- Tests:
  - Template rendering test to assert both links render when both are present
  - URL builder unit test to assert deterministic URL formatting for known input identifiers

### 7.4 Verification Approach

- Manual acceptance verification is required because external navigation success cannot be reliably asserted in unit tests.
- Unit tests should still validate:
  - Correct selection and labeling logic (both links shown).
  - Correct external-link attributes (`target`, `rel`).
  - Deterministic URL generation given a fixed NTSB identifier input.

## 8. Success Metrics

Primary success criterion:

- When clicking an NTSB link from the incident list, the user is taken to the correct NTSB web URL where they can view more data about the incident (not a PDF-only destination for the primary link).

Secondary success criteria:

- When both NTSB destinations are available, the UI exposes both (“NTSB Details” and “NTSB Docs”).
- The click-through works in both normal browsers and embedded preview contexts when opening in a new tab.

## 9. Open Questions

1. Which exact NTSB web URL pattern should be treated as canonical for “NTSB Details” going forward (CAROL detail vs. CAROL search deeplink on `data.ntsb.gov`)?
2. Which NTSB identifier(s) are consistently available in our stored `IncidentSource.source_data` payloads (e.g., `cm_mkey`, NTSB number), and which should be the primary key for building stable URLs?
3. Do we need a one-time migration to rewrite historical `source_url` values for NTSB, or is fix-forward ingestion sufficient initially?

