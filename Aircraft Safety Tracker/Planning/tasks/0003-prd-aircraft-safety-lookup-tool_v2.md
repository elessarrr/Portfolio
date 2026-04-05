# Product Requirements Document: Aircraft Safety History Lookup Tool v2.0

**ROOT DIRECTORY:** All work for this project should be performed within the `Aircraft Safety Tracker` directory.

**Project ID:** 0003  
**Created:** March 2026  
**Target Launch:** April 2026 (4-week sprint)  
**Author:** Raj  
**Previous Version:** 0002-prd-aircraft-safety-lookup-2.md  
**Domain Expert Validation:** Aviation safety regulator (DASA equivalent) confirmed use case

---

## 1. Introduction/Overview

### Problem Statement
V1.0 proved the concept: travelers want transparent aircraft safety data. **Expert feedback from an aviation safety regulator** revealed critical gaps:
1. **Root cause opacity:** Users can't filter by system failures (hydraulics, electrical, structural)
2. **Variant ambiguity:** "Boeing 737" includes 10+ variants with different safety profiles
3. **Single-source limitation:** ASN alone misses FAA/NTSB incident details
4. **Manual report analysis:** Key insights locked in PDF investigation reports, not databases

### Solution
V2.0 transforms the tool from a **consumer travel aid** into a **professional aviation safety intelligence platform** that regulators, operators, and safety analysts would actually use:
- **Root cause filtering** by aircraft system (hydraulics, electrical, avionics, structural, engine)
- **Granular variant tracking** (737-700 vs 737-800 vs 737 MAX 8)
- **Multi-source data aggregation** (ASN + FAA + NTSB)
- **AI report interrogation** (experimental) to extract structured data from PDF reports
- **Internal operator incident tracking** (future enterprise feature, scoped for now)

### Goal
Build a tool that **aviation safety professionals cite as their go-to research platform**, transitioning from portfolio piece to legitimate industry tool with potential B2B revenue path.

---

## 2. Goals

### Primary Goals
1. **Professional Credibility:** Secure endorsement from 3+ aviation safety regulators/professionals as a useful research tool
2. **Data Richness:** Aggregate 3+ authoritative sources (ASN, FAA, NTSB) into unified view
3. **Operational Intelligence:** Enable root cause analysis via system-level filtering (80%+ incidents tagged)
4. **Variant Precision:** Distinguish safety records across aircraft variants where data permits
5. **Portfolio Impact:** Generate interest from 5+ aviation companies/regulators for enterprise version

### Secondary Goals
1. **AI-Powered Insights:** Demonstrate experimental AI report interrogation (beta feature)
2. **Industry Validation:** Present at aviation safety conference or publish case study
3. **B2B Foundation:** Validate demand for internal incident tracking (operator near-misses)
4. **Open Source Contribution:** Release data aggregation framework for aviation community

---

## 3. User Stories

### Primary User: Aviation Safety Regulator
**As an aviation safety regulator,**  
I want to filter incidents by root cause system (e.g., all hydraulic failures on A320 family),  
So that I can identify systemic issues requiring regulatory intervention.

**Acceptance Criteria:**
- Filter incidents by: Hydraulics, Electrical, Avionics, Structural, Engine, Other
- Multi-select filters (show incidents affecting multiple systems)
- Export filtered results as CSV for further analysis

### Primary User: Airline Safety Manager
**As an airline safety manager,**  
I want to compare incident rates across aircraft variants (737-800 vs 737 MAX 8),  
So that I can make data-driven fleet procurement decisions.

**Acceptance Criteria:**
- Separate incident counts for each variant where ASN data distinguishes them
- Side-by-side comparison view for 2-3 variants
- Variant-specific AI summaries noting differences

### Primary User: Aviation Investigator
**As an aviation investigator researching a new incident,**  
I want to access full NTSB/FAA reports for similar historical incidents,  
So that I can identify precedent patterns and investigative pathways.

**Acceptance Criteria:**
- Direct links to NTSB final reports
- AI-extracted summaries from reports (experimental, clearly marked)
- Related incident suggestions based on aircraft model + root cause

### Secondary User: Aerospace Journalist
**As an aerospace journalist writing about aircraft safety,**  
I want to see which data sources corroborate incident claims,  
So that I can cite multiple authoritative references in my reporting.

**Acceptance Criteria:**
- Incidents show data source tags (ASN, FAA, NTSB)
- Conflicting data between sources is flagged
- Citation-ready incident URLs

---

## 4. Functional Requirements

### FR-1: Root Cause Filtering by System (MUST HAVE)

**The system must allow filtering incidents by aircraft system failure.**

- **FR-1.1:** Define system categories:
  - Hydraulics
  - Electrical
  - Avionics/Navigation
  - Structural
  - Engine/Propulsion
  - Flight Controls
  - Landing Gear
  - Environmental (pressurization, air conditioning)
  - Other/Unknown
- **FR-1.2:** Display multi-select checkboxes for system filters
- **FR-1.3:** Incidents can be tagged with multiple systems (e.g., electrical failure leading to hydraulic loss)
- **FR-1.4:** System tags derived from:
  - Manual tagging from ASN narrative analysis (AI-assisted)
  - Scraped from NTSB "Findings" section if available
  - User submissions (verified by admin before display)
- **FR-1.5:** Display system tag confidence score: "High" (from official report), "Medium" (AI-inferred), "Low" (user-suggested)
- **FR-1.6:** Export filtered results as CSV with columns: Date, Aircraft, Operator, System, Description, Source

### FR-2: Aircraft Variant Granularity (MUST HAVE)

**The system must distinguish between aircraft variants where data permits.**

- **FR-2.1:** Parse ASN data to extract variant specificity:
  - Boeing 737: -700, -800, -900, -900ER, MAX 7, MAX 8, MAX 9, MAX 10
  - Airbus A320 family: A318, A319, A320, A321 (distinguish CEO vs NEO where possible)
  - Other families as data permits
- **FR-2.2:** When ASN doesn't specify variant:
  - Tag incident as "Variant unknown"
  - Use AI to infer from operator/registration if possible (mark as "Inferred - verify source")
  - Do NOT guess—transparency over completeness
- **FR-2.3:** Aircraft detail pages show variant-specific statistics:
  - Incidents per variant
  - Fatal incidents per variant
  - Total flight hours per variant (if public data available)
- **FR-2.4:** Variant comparison view:
  - Select 2-3 variants side-by-side
  - Show relative incident rates normalized by years in service
  - AI summary highlighting safety differences

### FR-3: Multi-Source Data Aggregation (MUST HAVE)

**The system must aggregate incident data from ASN, FAA, and NTSB databases.**

**FR-3.1: Aviation Safety Network (ASN)**
- Continue scraping ASN as primary source
- Enhance scraping to capture more metadata (weather, phase of flight)

**FR-3.2: FAA Accident/Incident Database**
- Scrape https://www.faa.gov/data_research/accident_incident
- Extract: Date, Aircraft Type, Registration, Operator, Location, Injury Summary
- Match incidents to ASN data by date + registration
- Store FAA-specific fields: Investigating Agency, Report Status

**FR-3.3: NTSB Database**
- Scrape https://www.ntsb.gov/Pages/home.aspx (aviation query tool)
- Extract: NTSB ID, Probable Cause, Findings, Recommendations
- Link NTSB reports to ASN/FAA incidents
- Store PDF report URLs for full investigation details

**FR-3.4: Data Deduplication**
- Match incidents across sources using: Date + Aircraft Registration
- If same incident in multiple sources, create unified view
- Display data provenance: "Confirmed by ASN + NTSB" vs "ASN only"

**FR-3.5: Source Conflict Handling**
- If fatality counts differ between sources, show both with note: "ASN: 12 fatalities, NTSB: 13 (1 later death)"
- Flag significant discrepancies for manual review

**FR-3.6: Data Freshness Indicators**
- Show last scrape date per source
- Button to trigger manual refresh (admin only)
- Weekly automated updates

### FR-4: AI Report Interrogation (EXPERIMENTAL - MUST HAVE)

**The system should extract structured data from PDF investigation reports using AI.**

- **FR-4.1:** API endpoint for report analysis:
  - `POST /api/analyze-report`
  - Accepts: PDF URL or uploaded file
  - Returns: JSON with extracted fields
- **FR-4.2:** Extracted fields:
  - Root cause (primary system failure)
  - Contributing factors (list)
  - Investigation findings (summary)
  - Safety recommendations (list)
  - Narrative summary (3-5 sentences)
- **FR-4.3:** AI model requirements:
  - Must support long context (30k+ tokens for full reports)
  - Configurable via API URL (Gemini, Claude, GPT-4, local model)
  - Rate limiting: max 10 reports/hour (free tier safety)
- **FR-4.4:** UI display:
  - "AI Report Analysis" section clearly marked as **EXPERIMENTAL**
  - Disclaimer: "AI-extracted data may contain errors. Always verify against official report."
  - Link to full PDF report for verification
  - Feedback button: "Report inaccuracy"
- **FR-4.5:** Quality controls:
  - Manual spot-check 10% of AI extractions
  - If accuracy falls below 80%, disable feature
  - Log all extractions for future model fine-tuning

### FR-5: Internal Operator Incident Tracking (FUTURE - OUT OF SCOPE FOR V2.0)

**BACKLOG: Framework for integrating airline-internal incident data (near misses, internal reports).**

- **FR-5.1:** Not implemented in v2.0
- **FR-5.2:** Scoped as enterprise B2B feature
- **FR-5.3:** Requirements gathering:
  - Add feature request form: "What internal data would you want to integrate?"
  - Track requests from airlines, operators, safety managers
  - Use feedback to design enterprise API in v3.0

### FR-6: Enhanced Search and Filtering (MUST HAVE)

**Extend v1.0 search with new filtering dimensions.**

- **FR-6.1:** Advanced filter panel:
  - Root cause system (multi-select)
  - Aircraft variant (multi-select)
  - Data source (ASN, FAA, NTSB)
  - Date range
  - Fatalities (none, 1-10, 10-50, 50+)
  - Phase of flight (takeoff, cruise, landing, etc.)
  - Weather conditions (VMC, IMC)
- **FR-6.2:** Save filter presets:
  - "All hydraulic failures on Airbus A320 family"
  - "Fatal incidents in last 5 years"
  - Users can bookmark custom filters
- **FR-6.3:** Filter URL parameters:
  - `/aircraft/Boeing-737-800?filter=hydraulics&date_from=2020-01-01`
  - Shareable links for specific analyses

### FR-7: Data Transparency & Provenance (MUST HAVE)

**Extend v1.0 disclaimers with source attribution.**

- **FR-7.1:** Every incident displays source tags:
  - Icon badges: [ASN] [FAA] [NTSB]
  - Hover to see: "Last updated: 2024-03-15"
- **FR-7.2:** Data quality indicators:
  - "Verified by official investigation" (NTSB final report)
  - "Preliminary data" (FAA incident report, no final conclusion)
  - "Crowdsourced" (user-submitted system tags)
- **FR-7.3:** About page enhancements:
  - Methodology section: How we scrape, match, and deduplicate
  - Data coverage stats: "85% of incidents have NTSB confirmation"
  - Known limitations: "Variant data only available for post-2000 aircraft"
- **FR-7.4:** Citation tool:
  - "Cite this incident" button generates formatted citation
  - Formats: APA, MLA, Chicago
  - Includes access date and data sources

### FR-8: Performance & Scalability (MUST HAVE)

**Support 3x data volume (3 sources vs 1) without degrading UX.**

- **FR-8.1:** Database optimization:
  - Index on: aircraft_id, date, system_tags, data_source
  - Full-text search on incident descriptions
  - Pagination: 20 incidents per page (not 100+)
- **FR-8.2:** Caching strategy:
  - Cache filtered queries for 1 hour
  - Invalidate cache on data refresh
  - Pre-generate popular filter combinations
- **FR-8.3:** Load time targets:
  - Initial page load: < 2 seconds
  - Filter application: < 500ms
  - AI report analysis: < 30 seconds (with loading indicator)
- **FR-8.4:** Monitoring:
  - Log slow queries (> 1 second)
  - Alert if scraper fails for any source
  - Track AI API usage to avoid rate limits

---

## 5. Non-Goals (Out of Scope for V2.0)

### Explicitly NOT Building:
1. **Real-Time Flight Tracking:** Still focused on historical data, not live incident monitoring
2. **Airline Safety Ratings:** Focus remains on aircraft models, not airline operational safety
3. **Predictive Analytics:** No ML models predicting future incidents
4. **Mobile App:** Web interface only (responsive design sufficient)
5. **User Accounts/Social Features:** No login, profiles, or discussion forums
6. **Maintenance Records:** Still only publicly reported incidents, not routine maintenance
7. **International Databases (v2.0):** EASA, CASA, other non-US regulators deferred to v3.0
8. **NASA ASRS Integration:** Deferred to v3.0 (different data format, requires separate scraper)
9. **Commercial Licensing:** Remains free, open-source tool for v2.0
10. **Internal Operator Data:** Enterprise feature, not public tool (see FR-5)

---

## 6. Design Considerations

### Design Philosophy
**Professional tool aesthetic**: Transition from "consumer travel app" to "aviation safety research platform."

### Key Design Changes from V1.0:
1. **Filter Panel:** Persistent left sidebar with collapsible sections
2. **Data Source Badges:** Visual indicators for ASN/FAA/NTSB
3. **Variant Comparison:** Side-by-side table view
4. **Advanced Mode:** Toggle between "Simple" (v1.0 UX) and "Advanced" (all filters visible)
5. **Export Buttons:** CSV download for filtered results

### Visual Style Updates:
- **Color Palette:**
  - Primary: Deep blue (#1e3a8a) - unchanged
  - Accent: Amber (#f59e0b) for warnings - unchanged
  - NEW: Green (#10b981) for "Verified by NTSB"
  - NEW: Orange (#f97316) for "AI-extracted (verify)"
  - NEW: Gray badges for data sources
- **Typography:**
  - Add small caps for system tags: "HYDRAULICS", "ELECTRICAL"
  - Monospace for NTSB report IDs: "NYC96FA099"
- **Icons:**
  - Checkmark for verified data
  - Question mark for AI-inferred
  - Warning triangle for experimental features

### New UI Components:
1. **Filter Sidebar:** Sticky left panel, 280px width, collapsible on mobile
2. **Source Badges:** Small pills with icons [ASN] [FAA] [NTSB]
3. **Variant Comparison Table:** Responsive grid layout
4. **AI Analysis Card:** Distinct styling with warning border for experimental features
5. **Export Dropdown:** CSV, JSON, citation formats
6. **Report Preview Modal:** Inline PDF viewer for NTSB reports

---

## 7. Technical Considerations

### Technology Stack (Additions to V1.0)

**Backend (Flask):**
- **NEW: Multi-source scrapers:**
  - `scripts/scrape_faa.py` - FAA database scraper
  - `scripts/scrape_ntsb.py` - NTSB database scraper
  - `scripts/deduplicate.py` - Cross-source incident matching
- **NEW: AI integration:**
  - `app/services/report_analyzer.py` - AI API client (configurable endpoint)
  - Support for: Gemini, Claude, GPT-4, local models via unified interface
- **NEW: Advanced search:**
  - Full-text search with SQLite FTS5
  - Multi-dimensional filtering via SQLAlchemy

**Database Schema Updates:**
```sql
-- New tables
CREATE TABLE IncidentSource (
    id INTEGER PRIMARY KEY,
    incident_id INTEGER,
    source_name TEXT, -- 'ASN', 'FAA', 'NTSB'
    source_url TEXT,
    source_data JSON, -- Raw data from source
    last_updated TIMESTAMP
);

CREATE TABLE SystemTag (
    id INTEGER PRIMARY KEY,
    incident_id INTEGER,
    system_name TEXT, -- 'Hydraulics', 'Electrical', etc.
    confidence TEXT, -- 'High', 'Medium', 'Low'
    tagged_by TEXT, -- 'ASN', 'AI', 'User'
    created_at TIMESTAMP
);

CREATE TABLE AircraftVariant (
    id INTEGER PRIMARY KEY,
    model_id INTEGER, -- FK to Aircraft
    variant_name TEXT, -- '737-800', 'A320neo'
    years_in_service TEXT,
    total_incidents INTEGER,
    fatal_incidents INTEGER
);

CREATE TABLE ReportAnalysis (
    id INTEGER PRIMARY KEY,
    incident_id INTEGER,
    report_url TEXT,
    root_cause TEXT,
    contributing_factors JSON,
    findings TEXT,
    recommendations JSON,
    narrative_summary TEXT,
    analysis_confidence REAL, -- 0.0-1.0
    analyzed_at TIMESTAMP,
    ai_model TEXT -- 'gemini-1.5-flash', 'claude-3-opus', etc.
);
```

### Data Collection Strategy (V2.0)

**Phase 1 (Week 1): Enhanced ASN Scraping**
- Update `scripts/scrape_boeing.py` and `scripts/scrape_airbus.py`
- Extract variant from model name (parse "Boeing 737-800 (WL)")
- Scrape additional metadata: weather, phase of flight
- Manual tagging of 50 sample incidents for AI training

**Phase 2 (Week 2): FAA Database Scraping**
- Build `scripts/scrape_faa.py`
- Target: https://www.faa.gov/data_research/accident_incident
- Extract: Date, N-number, Make/Model, Location, Injury Level
- Match to ASN via date + registration

**Phase 3 (Week 2-3): NTSB Database Scraping**
- Build `scripts/scrape_ntsb.py`
- Target: https://www.ntsb.gov/_layouts/ntsb.aviation/index.aspx
- Extract: NTSB ID, Event Date, Make/Model, Probable Cause
- Scrape PDF report URLs
- Trigger AI analysis on subset (100 reports for testing)

**Phase 4 (Week 3): Deduplication & Matching**
- Build `scripts/deduplicate.py`
- Match logic:
  1. Exact match: date + registration
  2. Fuzzy match: date ± 1 day + model + location
  3. Manual review for conflicts
- Create unified IncidentSource records

**Phase 5 (Week 4): AI Report Analysis**
- Configure AI API client with retry logic
- Process 500 NTSB reports (rate-limited)
- Manual QA on 10% sample
- Store results in ReportAnalysis table

### AI Report Analysis API

**Endpoint Design:**
```python
POST /api/v1/analyze-report
Content-Type: application/json

{
  "report_url": "https://www.ntsb.gov/investigations/...",
  "report_text": "optional_full_text_if_pre_extracted",
  "model": "gemini-1.5-flash" // or "claude-3-opus", "gpt-4-turbo"
}

Response:
{
  "root_cause": "Hydraulic system failure due to O-ring degradation",
  "contributing_factors": [
    "Inadequate maintenance procedures",
    "Environmental stress (temperature cycling)"
  ],
  "findings": "Investigation revealed...",
  "recommendations": [
    "Inspect all O-rings on fleet",
    "Update maintenance manual"
  ],
  "narrative_summary": "3-5 sentence summary...",
  "confidence": 0.85,
  "model_used": "gemini-1.5-flash",
  "processed_at": "2024-03-15T10:30:00Z"
}
```

**Supported Models (via Adapter Pattern):**
- Google Gemini 1.5 Flash (default, free tier)
- Anthropic Claude 3 Opus/Sonnet
- OpenAI GPT-4 Turbo
- Local models via Ollama API
- Configurable via environment variable: `AI_REPORT_MODEL=gemini-1.5-flash`

### Performance Targets

- **Database size:** ~10,000 incidents across 3 sources (3x growth)
- **Query latency:** < 100ms for filtered searches (indexed properly)
- **Scraping frequency:** Weekly for ASN/FAA, monthly for NTSB (manual trigger available)
- **AI processing:** Batch 100 reports at a time, ~30 seconds per report
- **Caching:** Aggressive caching for popular filters (80% hit rate target)

---

## 8. Success Metrics

### Primary Metrics (First Month Post-Launch)

**1. Professional User Adoption:**
- **Target:** 10+ confirmed aviation professionals (regulators, safety managers, investigators) using the tool
- **Measure:** Email signups for "Professional Users" newsletter
- **Validation:** LinkedIn endorsements from industry profiles

**2. Usage Growth:**
- **Target:** 1,000+ total searches (2x v1.0 target)
- **Target:** 300+ unique visitors
- **Target:** 50+ distinct aircraft variants searched

**3. Data Quality:**
- **Target:** 80%+ incidents tagged with root cause system
- **Target:** 70%+ incidents matched across 2+ data sources
- **Target:** AI report analysis accuracy > 80% (manual validation)

**4. Feature Engagement:**
- **Target:** 40%+ users apply root cause filters
- **Target:** 30%+ users compare aircraft variants
- **Target:** 20%+ users export filtered data (CSV)
- **Target:** 10+ AI report analyses requested

**5. B2B Interest:**
- **Target:** 5+ airlines/regulators inquire about enterprise version
- **Target:** 50+ feature requests for internal operator data integration
- **Target:** 1+ aviation safety organization requests data partnership

### Secondary Metrics

**6. Expert Validation:**
- Get tool reviewed by domain expert (DASA equivalent acquaintance)
- Receive written endorsement or testimonial
- Identify 2-3 feature gaps for v3.0 roadmap

**7. Content/Community:**
- Publish case study: "How V2.0 Identified a Hidden Pattern in A320 Hydraulic Failures"
- Submit to Hacker News / aviation subreddits
- Present at virtual aviation safety conference (if opportunity arises)

**8. Technical Performance:**
- Zero critical data quality bugs
- Uptime > 99.5%
- AI analysis success rate > 90% (excluding rate limits)

### Long-Term Indicators (3-6 Months)

**9. Industry Recognition:**
- Cited by aviation journalist or safety blog
- Featured in aviation professional newsletter
- Invited to partner with aviation organization

**10. Revenue Validation (Future):**
- 20+ expressions of interest in paid enterprise tier
- 1+ pilot deployment with airline safety team
- Clear path to B2B SaaS model

---

## 9. Open Questions

### Data Access & Legal
1. **Q:** Do FAA/NTSB databases have scraping restrictions or rate limits?  
   **A:** Research robots.txt and terms of service; may need to contact for API access

2. **Q:** Can we legally redistribute aggregated incident data?  
   **A:** All sources are public domain, but verify citation requirements

3. **Q:** Do we need liability insurance for professional tool used by regulators?  
   **A:** Consult lawyer if tool gains traction beyond portfolio use

### Technical Implementation
4. **Q:** How do we handle NTSB report PDFs that aren't machine-readable (scanned images)?  
   **A:** Use OCR (Tesseract) before AI analysis, or skip if quality too low

5. **Q:** What's the fallback if AI API rate limits hit during batch processing?  
   **A:** Queue-based processing with exponential backoff, process overnight

6. **Q:** Should variant comparison be live or pre-computed?  
   **A:** Pre-compute stats nightly, live query for custom filters

### User Experience
7. **Q:** Do we show "zero incidents" for variants with no recorded incidents?  
   **A:** Yes, with note: "No incidents in database (may be recent variant or excellent record)"

8. **Q:** How do we handle user-submitted system tags (crowdsourcing)?  
   **A:** Allow submissions via form, admin reviews before publishing, track contributor reputation

9. **Q:** Should we add user accounts for saving filters/analyses?  
   **A:** Not in v2.0, but capture email for future feature notification

### Go-to-Market
10. **Q:** Where do aviation professionals hang out online?  
    **A:** Professional Pilots Rumour Network (PPRuNe), r/aviation, LinkedIn aviation groups

11. **Q:** Should we charge for API access from day one?  
    **A:** No, build user base first, then introduce paid tier for high-volume API users

12. **Q:** What's the minimum viable enterprise feature set?  
    **A:** Internal incident integration + role-based access + audit logs

---

## 10. Risks & Mitigation

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| **FAA/NTSB scraping blocked** | High | Medium | Contact agencies for data partnership; fall back to ASN-only if needed |
| **AI report analysis accuracy < 80%** | High | Medium | Manual QA process; disable feature if below threshold; collect training data for fine-tuning |
| **Variant parsing errors** | Medium | High | Conservative approach: "Unknown" when uncertain; manual correction interface |
| **Legal challenge from data source** | High | Low | Prominent attribution; cease if requested; pivot to API partnerships |
| **Performance degradation (3x data)** | Medium | Medium | Aggressive indexing; pagination; caching; monitor query times |
| **Scope creep (too ambitious)** | Medium | High | Strict 4-week timeline; cut experimental features if behind schedule |
| **Expert user rejection** | High | Low | Direct feedback loop with DASA acquaintance; iterate based on real usage |

---

## 11. Dependencies & Timeline

### Dependencies:
1. **V1.0 completion** - Base infrastructure must be solid
2. **AI API access** - Gemini/Claude/GPT-4 accounts and rate limits understood
3. **Domain expert availability** - DASA acquaintance available for testing in Week 4
4. **Data source stability** - FAA/NTSB sites don't change structure mid-development

### 4-Week Sprint Breakdown:

**Week 1: Enhanced Scraping + Variant Granularity**
- Update ASN scrapers for variant parsing
- Build FAA scraper
- Database schema updates
- Manual tag 50 incidents for AI training

**Week 2: NTSB Integration + Deduplication**
- Build NTSB scraper
- Implement deduplication logic
- Test cross-source matching
- Begin AI report analysis (first 100 reports)

**Week 3: Root Cause Filtering + AI Analysis**
- Build root cause tagging pipeline (AI-assisted)
- Implement filter UI
- Complete AI report analysis on 500 reports
- Manual QA on 10% sample

**Week 4: Polish + Expert Testing**
- Variant comparison feature
- Export functionality
- Data quality checks
- Send to DASA acquaintance for real-world testing
- Iterate based on feedback
- Deploy to production

### Critical Path:
1. Database schema changes (blocks everything)
2. FAA/NTSB scrapers (blocks deduplication)
3. Deduplication logic (blocks unified views)
4. AI report analysis (can be done in parallel, but needed for full feature set)

---

## 12. Appendix

### V3.0 Roadmap (Backlog)

**International Database Integration:**
- EASA (European Aviation Safety Agency)
- CASA (Civil Aviation Safety Authority - Australia)
- Transport Canada
- UK CAA (Civil Aviation Authority)

**NASA ASRS Integration:**
- Taxonomy mapping (https://asrs.arc.nasa.gov/search/database.html)
- Anonymous incident reporting data
- Near-miss analysis

**Enterprise B2B Features:**
- **Internal Operator Incident Tracking:**
  - API for airlines to submit internal incidents
  - Role-based access control (safety manager, investigator, exec)
  - Benchmarking against industry averages
  - Anonymized data sharing between operators
- **Advanced Analytics:**
  - Trend detection (emerging failure patterns)
  - Fleet-specific risk scoring
  - Predictive maintenance indicators
- **Compliance Tools:**
  - Regulatory report generation
  - Audit trail for investigations
  - Integration with SMS (Safety Management Systems)

**Machine Learning Features:**
- Incident similarity clustering
- Failure pattern prediction
- Automated root cause categorization (supervised learning)

### Target Aircraft Coverage (V2.0)

**No change from V1.0** - still ~40 models (Boeing + Airbus commercial)  
Focus is on **data depth** (3 sources) not **breadth** (more manufacturers)

**Future expansion (V3.0):**
- Embraer (E-Jets family)
- Bombardier/Airbus Canada (CRJ, A220)
- Regional turboprops (ATR, Dash 8)

### Reference Materials

**Data Sources:**
- Aviation Safety Network: https://aviation-safety.net/
- FAA Accident/Incident Database: https://www.faa.gov/data_research/accident_incident
- FAA ASIAS: https://www.asias.faa.gov/apex/f?p=100:1
- NTSB Aviation Database: https://www.ntsb.gov/Pages/home.aspx
- NASA ASRS: https://asrs.arc.nasa.gov/

**Domain Expert Feedback (Summarized):**
> "Introducing a feature to filter by root cause (by system) could assist other operators and regulators when faced with similar common issues. Aircraft type/model would need more granularity... If you look at existing databases from regulators and investigation agencies and look to create something better/different with better functionality, UI and more filtering then you would be onto something."  
> — Aviation Safety Regulator (DASA equivalent)

**Competitive Landscape:**
- **SKYbrary:** Aviation safety knowledge base (static content, no search)
- **FlightGlobal Safety Database:** Paywalled, not consumer-friendly
- **JACDEC:** Airline safety rankings, not aircraft-specific
- **Our Differentiator:** Free, multi-source, system-level filtering, variant granularity

---

## Approval & Sign-off

**Created by:** Raj  
**Reviewed by:** Aviation safety regulator (informal consultation)  
**Date:** March 2026  
**Status:** Ready for Development  
**Next Step:** Generate task breakdown → Begin Week 1 sprint  

**Key Validation:** Domain expert confirmed: *"Yes absolutely. As a regulator in DASA I know I would [use this tool]!"*

---

*This PRD is a living document and will be updated based on expert testing feedback and technical discoveries during implementation.*
