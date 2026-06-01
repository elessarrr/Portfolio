# Product Requirements Document: WA Incident Press Enrichment & Investigation FAQ

## 1. Introduction / Overview

When NTSB assigns a "WA" (World Aviation) case number to an incident — e.g., `DCA26WA031` — it means the accident occurred outside the United States. Under ICAO Annex 13, the country where the accident happened leads the investigation and publishes the official report. NTSB participates only as an observer ("state of design" for US-manufactured aircraft) and does not publish its own docket. The result: `data.ntsb.gov/Docket/?NTSBNumber=DCA16WA084` returns "The docket for this investigation has not been released" — permanently, not as a timing delay.

After PRD-0019 Phase 6 marks these records `is_active=False`, users will see no external link at all for WA incidents. This PRD closes the gap in two ways:

1. **Press enrichment**: A background enrichment process searches for the most credible publicly available news article or press report for each WA incident and stores it as a new `IncidentSource` row, giving users a readable external reference.
2. **FAQ page**: A new `/faq` route explains the ICAO Annex 13 investigation system, why NTSB dockets may not exist for international incidents, and provides links to every major national aviation investigation authority so users can search those sources directly.

---

## 2. Goals

- Ensure every WA-coded NTSB incident with no active external link has at least one press article linked, so users can verify the incident happened and learn more
- Surface the most credible available article (Aviation Herald prioritised, then major news wires), not just any article
- Provide a standalone educational FAQ page that explains the international investigation system and lists all major foreign aviation authorities with links to their homepages
- Link WA incidents with no active NTSB docket directly to the FAQ page so users understand the structural reason rather than assuming the app is broken

---

## 3. User Stories

- **As a user** viewing a Boeing 747 incident with no source link, I want to see a press article about the incident so I can confirm it happened and learn the basic facts.
- **As a user** clicking an incident link labelled `avherald.com`, I want to be taken to Aviation Herald's coverage of that specific incident.
- **As a user** who notices an incident has no official NTSB link, I want a clear explanation of why — and a way to find the foreign investigation authority's report myself.
- **As a researcher**, I want a single page listing all major national aviation safety investigation authorities with their website links, so I can look up reports that aren't in this app.

---

## 4. Functional Requirements

### Phase 1 — Press Article Enrichment (Background Job)

1. The system must identify all `IncidentSource` records where `source_name = 'NTSB'` and `is_active = False` and the associated `Incident` has no other active `IncidentSource` with a non-null `source_url`. These are the WA incidents with no usable external link. *(Prerequisite: PRD-0019 Phase 6 must be complete so WA records are already marked `is_active=False`.)*

2. For each such incident, the enrichment process must search for a press article using the following tier order. **Note:** Aviation Herald's own site search engine is broken and returns static content regardless of query — Tier 1 must use an external search API with a `site:avherald.com` modifier, not a direct query to Aviation Herald's search endpoint.
   - **Tier 1 — Aviation Herald** (`avherald.com`): query `site:avherald.com [operator] [location] [year]` via the configured search API. If operator is null, omit it. Accept the first result on `avherald.com`.
   - **Tier 2 — Major news wires**: query `[operator] [aircraft type] [location] [year] accident` restricted to `reuters.com OR apnews.com OR bbc.com OR bbc.co.uk OR afp.com` via the configured search API. Accept the first result from any of these domains.
   - **Tier 3 — General web**: same base query as Tier 2 without domain restriction via the configured search API. Accept only results from recognisable news organisations — not social media, forums, or aggregator spam.
   - If no credible result is found after Tier 3, skip the incident and log it as `enrichment_status = 'not_found'` — do not store a low-quality link.

3. The enrichment process must store each found article as a new row in the `incident_source` table with the following exact values:

   | Column | Value |
   |---|---|
   | `incident_id` | The incident's `id` |
   | `source_name` | `'MEDIA'` |
   | `source_url` | The full article URL (must be a valid, reachable URL) |
   | `source_record_id` | The article's domain name only, e.g. `avherald.com` or `reuters.com` |
   | `report_url` | `null` |
   | `is_active` | `True` |
   | `confidence_level` | `'Low'` |
   | `source_data` | JSON: `{"title": "<article headline>", "domain": "<domain>", "tier": <1|2|3>, "searched_at": "<ISO8601 timestamp>", "found_by": "agent"}` |
   | `last_validated_at` | `null` (will be picked up by weekly cron) |

4. The enrichment process must be idempotent: if a `MEDIA` IncidentSource already exists for an incident, skip that incident rather than creating a duplicate.

5. The enrichment process must log a summary on completion: total incidents checked, articles found (by tier), incidents skipped (already enriched), incidents with no result found.

6. A found article URL must be validated (HTTP GET, status 200, non-empty body) before it is stored. If the URL is unreachable or returns an error, discard it and continue searching.

### Phase 2 — Template: Display MEDIA Source Links

7. The templates `incident_list.html` and `global_incident_list.html` already render all active `IncidentSource` rows by source name. No structural change is needed — `MEDIA` rows will render automatically as a link labelled with `source.source_record_id` (the domain name), e.g. `avherald.com ↗`.

8. The template must not add any special badge, colour, or label distinguishing `MEDIA` links from official source links. Display is identical to other sources.

### Phase 3 — Template: FAQ Link on WA Incidents

9. In `incident_list.html` and `global_incident_list.html`, for each incident where:
   - At least one `IncidentSource` with `source_name = 'NTSB'` exists in the incident's sources (active or inactive), AND
   - That NTSB source has `is_active = False` (docket unreleased), AND
   - There is no other active NTSB source for the same incident

   …the template must render a small informational note below the source badges:
   ```
   No official NTSB docket — <a href="/faq#international-investigations">why?</a>
   ```
   This link must open in the same tab (no `target="_blank"`).

10. The note must not appear on incidents where the NTSB source is active (valid docket exists) or where there is no NTSB source at all.

### Phase 4 — FAQ Page (`/faq`)

11. A new route `GET /faq` must be added to `app/routes.py`, rendering a new template `app/templates/faq.html`.

12. The FAQ page must include a section with the anchor `#international-investigations` containing:
    - A plain-English explanation of ICAO Annex 13: the country of the accident leads the investigation; NTSB participates as observer for US-manufactured aircraft; NTSB does not publish its own docket for these cases ("WA" cases).
    - The statement that "docket not released" for a WA case is permanent — not a timing delay.
    - A note that the official investigation report will be published by the relevant national authority.

13. The FAQ page must include a section listing national aviation investigation authorities, including (at minimum):

    | Authority | Country / Region | URL |
    |---|---|---|
    | ICAO | International (governing body) | https://www.icao.int |
    | NTSB | United States | https://www.ntsb.gov |
    | BEA | France | https://www.bea.aero |
    | AAIB | United Kingdom | https://www.gov.uk/aaib |
    | JTSB | Japan | https://www.mlit.go.jp/jtsb |
    | ATSB | Australia | https://www.atsb.gov.au |
    | TSB | Canada | https://www.tsb.gc.ca |
    | BFU | Germany | https://www.bfu-web.de |
    | DGAC | France (civil aviation authority, separate from BEA) | https://www.ecologie.gouv.fr/direction-generale-de-laviation-civile-dgac |
    | AIIBD | Brazil (CENIPA) | https://www.gov.br/defesa/pt-br/assuntos/aeronautica/cenipa |
    | AIIB | China | https://www.caac.gov.cn |
    | ECAA / EASA | European Union (safety agency) | https://www.easa.europa.eu |
    | CAA | New Zealand | https://www.caa.govt.nz |
    | CIAIAC | Spain | https://www.mitma.gob.es/recursos_mfom/010720190944a.pdf (CIAIAC homepage) |
    | AIB | Norway, Sweden, Denmark (joint) | https://www.havarikommisjonen.no |
    | ANSV | Italy | https://www.ansv.it |
    | TRAFI / Traficom | Finland | https://www.traficom.fi |
    | ACAR | South Korea | https://www.molit.go.kr |
    | AIBD | India (AAIB India) | https://aaib.gov.in |
    | SACAA | South Africa | https://www.caa.co.za |
    | GCAA | UAE | https://www.gcaa.gov.ae |
    | GACA | Saudi Arabia | https://gaca.gov.sa |
    | DGCA | Indonesia | https://hubud.dephub.go.id |
    | DGCA | Thailand | https://www.aviation.go.th |
    | AIIB | Russia (IAC) | https://mak-iac.org |
    | TATIP | Turkey (AAIA) | https://www.shgm.gov.tr |

14. The FAQ page must be linked from the site navigation (header or footer) so it is discoverable without arriving via an incident card.

15. All external authority links must open in a new tab (`target="_blank"` with `rel="noopener noreferrer"`).

---

## 5. Non-Goals (Out of Scope)

- Automatically finding or linking foreign authority investigation reports (BEA, AAIB, JTSB, etc.) — this is a future enhancement
- Real-time web search at page-render time (all enrichment is background/offline)
- Enriching incidents that already have a valid source link (only WA incidents with no active link are targets)
- Showing multiple press articles per incident (single most credible result only)
- Translating foreign-language authority pages
- Enriching FAA_AIDS or FAA_SDR incidents (different problem, different PRD)
- A feedback mechanism for users to suggest better article links

---

## 6. Design Considerations

- The FAQ page should match the existing site styling (Tailwind CSS, same header/footer as other pages).
- The `#international-investigations` section should appear first or near the top so the anchor link from incident cards arrives at a readable, contextual position.
- The authority table on the FAQ should be clearly formatted and scannable — consider grouping by region (Americas, Europe, Asia-Pacific, Middle East/Africa).
- The "No official NTSB docket — why?" note on incident cards should be visually subtle — small grey text, not a warning or error indicator. The incident happened; this is just context about link availability.

---

## 7. Technical Considerations

- **Prerequisite**: PRD-0019 Phase 6 must be complete before Phase 1 of this PRD. WA NTSB records must already be marked `is_active=False` so the enrichment job can correctly identify the target incident set.
- **Search API backend (primary — Google Custom Search API):** Set `GOOGLE_CSE_API_KEY` (API key) and `GOOGLE_CSE_CX` (programmable search engine ID) environment variables. Free tier: **100 queries/day**. At a maximum of 3 searches per incident (one per tier) and 197 target incidents, worst-case total is **591 searches** — achievable in 6 days at 100/day via a daily cron. Configure the Programmable Search Engine to search the entire web (not restricted to specific sites); site-restriction is handled in the query string (`site:avherald.com`). Obtain at: `console.developers.google.com` (Custom Search API) + `programmablesearchengine.google.com` (CX ID).
- **Search API backend (secondary — SerpAPI):** Set `SERPAPI_API_KEY`. Free tier: 100 queries/month. Used as fallback if Google CSE is unavailable.
- **Search API backend (tertiary — DuckDuckGo HTML scraping):** No key required. Works from home/residential IPs but is Cloudflare-blocked from cloud/server environments. Last resort.
- **Search backend priority order in `app/services/web_search.py`:** Google CSE → SerpAPI → DuckDuckGo HTML. The file already exists and must be updated to add Google CSE as the first backend. The SerpAPI and DuckDuckGo backends are already implemented.
- **Daily cron for incremental enrichment:** Run `PYTHONPATH=. .venv/bin/flask import-data enrich-wa-incidents --max-queries 90` daily (90 leaves headroom for other Google API usage). The `--max-queries` flag must be added to the CLI command to honour the daily quota. The job is idempotent — re-running skips already-enriched incidents automatically.
- **Enrichment execution**: The `flask import-data enrich-wa-incidents` CLI command already exists in `app/ingestion/cli.py`. It executes the Tier 1 → 2 → 3 search sequence per incident and writes results directly to the `incident_source` table using the exact column values specified in requirement 3.
- **Idempotency**: The command queries `SELECT id FROM incident_source WHERE incident_id = ? AND source_name = 'MEDIA'` before inserting, and skips if a row already exists.
- **Template isolation for FAQ link** (requirement 9): In Jinja2, use `incident.sources.all()` (all sources, not just active) to check for an inactive NTSB record. Example logic:
  ```
  {% set all_ntsb = incident.sources.all()|selectattr('source_name', 'equalto', 'NTSB')|list %}
  {% set inactive_ntsb = all_ntsb|rejectattr('is_active')|list %}
  {% set active_ntsb = all_ntsb|selectattr('is_active')|list %}
  {% if inactive_ntsb and not active_ntsb %}
    <!-- show FAQ link -->
  {% endif %}
  ```
- **`MEDIA` in existing source priority order**: `apply_source_priority_order()` in `routes.py` assigns priorities to NTSB, FAA_AIDS, FAA_SDR, ASN. Add `MEDIA` with the lowest priority (e.g., priority 5, `else_=99` fallback covers it already — no code change needed unless explicit ordering is desired).
- **Link validation**: The weekly `validate_incident_links.py` cron will pick up new `MEDIA` IncidentSource rows and validate them the same as ASN/FAA sources (standard `source_url` HEAD check). No special handling required.
- **FAQ route**: Add `@bp.route('/faq')` to `app/routes.py`. The template is static content — no DB queries needed.

---

## 8. Success Metrics

- **Enrichment coverage**: ≥ 70% of WA NTSB incidents with no active link receive a `MEDIA` IncidentSource row after the enrichment job runs
- **Tier distribution**: ≥ 50% of found articles come from Tier 1 (Aviation Herald) or Tier 2 (major wires), indicating credibility discipline
- **Zero broken links stored**: All stored `MEDIA` source_urls return HTTP 200 at time of insertion (validated before write)
- **FAQ discoverability**: `/faq` is reachable from the main navigation; `#international-investigations` anchor resolves correctly from incident card links
- **No regression**: Incidents with valid active NTSB sources do not display the "No official NTSB docket" note

---

## 9. Open Questions

- Should the FAQ eventually include a second section covering other common questions (e.g., "What is FAA AIDS data?", "Why are some incidents missing fatality counts?")? Out of scope for this PRD but the `/faq` route is a natural home for these.
- For the CIAIAC (Spain) and some smaller authorities, homepage URLs should be verified before the FAQ goes live — some of these may have moved.
- Should `MEDIA` sources appear in the export CSV (`/aircraft/<id>/incidents/export.csv`)? If so, the export logic in `routes.py` needs no change (it already exports all active sources), but the column label may need clarification.
