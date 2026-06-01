# 26 Apr 2026 - FAA_AIDS URL Recovery Assessment

## Scope

- Task reference: `tasks-0019-prd-source-link-attribution-remediation.md` (Phase 4.1 and 4.4).
- Objective: determine whether FAA_AIDS `IncidentSource` rows can be assigned usable `source_url` values from existing stored data or a deterministic URL pattern.

## Findings

- Local DB sample audit (`25` FAA_AIDS rows, requirement was `20+`) shows:
  - `source_data` payloads are coded field maps (`c1`, `c2`, ...).
  - No URL/link keys present in sampled payloads.
  - No URL-like string values found in sampled payloads.
- Aggregate counter check shows `source_url` is currently unset for FAA_AIDS:
  - `0 / 157342` rows have non-null `source_url`.
- URL pattern probe:
  - Candidate FAA brief endpoint tested:
    - `https://www.asias.faa.gov/apex/f?p=100:18:::NO::AP_BRIEF_RPT_VAR:<source_record_id>`
  - For sampled FAA_AIDS IDs (example `19850101000039A`), page shell loads but brief content block is empty.
  - Conclusion: `source_record_id` is not a reliable direct URL parameter for deterministic per-record linking.

## Decision

- FAA_AIDS per-record `source_url` cannot be recovered from currently stored `source_data`.
- No deterministic, validated URL pattern is currently available from `source_record_id`.
- Treat this as a known limitation for now; do not populate synthetic or guessed URLs.

## Next Step

- Keep Phase 4.2/4.3 open pending a verified FAA-supported lookup key or documented API/search endpoint that can deterministically resolve individual record URLs.
