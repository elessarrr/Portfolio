# Observation: Why PRD-0019 Phase 6 Body-Check Never Triggered

Date: 2026-05-03
Related: `0019-prd-source-link-attribution-remediation.md` (Phase 6), `tasks-03052026-wa-suppression-and-enrichment.md`

## Summary

The existing Phase 6 suppression check is effectively dead code in production data.

## Findings

- The implemented body-check targets `data.ntsb.gov/Docket/` URLs.
- Current `IncidentSource` records for `source_name='NTSB'` use `carol.ntsb.gov/investigations/detail/...` URLs instead.
- The CAROL detail page is a React SPA and relies on client-side JavaScript rendering.
- Because the server response is not the expected docket HTML body, the current body-content check never matches.
- DB review found zero `data.ntsb.gov/Docket/` URLs among active NTSB incident sources in scope.

## Impact

- WA-coded NTSB records were not being marked inactive by the intended Phase 6 logic.
- The enrichment process was operating on the wrong target set.

## Corrective Direction

Use NTSB event-id pattern matching (`source_record_id LIKE '_____WA%'`) for suppression, instead of body-checking CAROL detail pages.
