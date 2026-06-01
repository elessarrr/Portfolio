# 22 Apr Observations

## NTSB Click-Through Issue (`net::ERR_ABORTED`)

- **Observed error:** `net::ERR_ABORTED https://carol.ntsb.gov/investigations/detail/91271`
- **User impact:** Clicking NTSB source link may fail to open incident detail as expected.

### What We Confirmed

- Our code constructs NTSB detail links in:
  - `app/ingestion/importers/ntsb_importer.py`
  - Current format: `https://carol.ntsb.gov/investigations/detail/{cm_mkey}`
- A direct HTTP check to `https://carol.ntsb.gov/investigations/detail/91271` returns `200 text/html` (SPA shell), not a server-side 404.
- This suggests URL format is not obviously broken at HTTP layer, but detail rendering may fail client-side (or be blocked in preview/browser context).

### Most Likely Cause

- CAROL detail pages are SPA-driven and may rely on client-side API calls/session/cookies.
- In some environments (preview iframe/pop-up restrictions, strict privacy settings, third-party script/network blocking), navigation can show `net::ERR_ABORTED`.
- So this appears to be an external-site/runtime behavior issue, not a malformed URL bug in our backend string formatting.

### Recommended Fixes

1. **Short-term UX fallback**
- Prefer `report_url` (PDF) when available, since it is often more stable than SPA detail pages.
- Keep NTSB detail URL as secondary fallback.

2. **Link hardening**
- Add `rel="noopener noreferrer"` on external links.
- Optionally show a small hint: "If this link fails, try opening in a new browser tab directly."

3. **Data quality guardrail**
- During ingestion, keep both `source_url` and `report_url` when present.
- Optionally add a periodic checker for dead/flaky external links and flag rows.

4. **Optional product improvement**
- Add a "Copy URL" button next to NTSB links for manual open if browser blocks navigation.

### Suggested Next Engineering Step

- Update incident link selection logic in template/routes:
  - For NTSB, use `report_url` first when present.
  - Otherwise use `source_url`.
- Add/adjust tests to verify this preference behavior.

---

## Manufacturer Search Missing Autocomplete / Fuzzy Dropdown

- **Observed issue:** When typing an airplane manufacturer/model into the search input, there is no dropdown list of suggestions/options.
- **Expected behavior:** Show an autocomplete dropdown (fuzzy-search-like) with matching aircraft/manufacturer options while typing, similar to earlier versions of the app.
- **User impact:** Users have to guess the exact string; discovery is worse and search feels “broken” compared to the previous UX.
- **Suggested direction:** Re-introduce the autocomplete dropdown behavior (likely HTMX-driven) so typing “Boeing 74” offers suggestions like “Boeing 747”, etc.
