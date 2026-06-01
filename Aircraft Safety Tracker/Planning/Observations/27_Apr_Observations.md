# 27 Apr Observations

## 1. NTSB Link to "Docket Not Released" Page

- **Observed Issue**: Clicking on the 'NTSB' and 'Details' links for a specific Boeing 747 incident (Date: 2025-11-13, Location: N'Djamena, OF, Operator: Fly Pro) leads to an NTSB page stating "The docket for this investigation has not been released."
- **Root Cause Hypothesis**: This indicates that while the NTSB incident record exists, the detailed investigation docket or report is not yet publicly available on the NTSB website. The application currently links directly to this page without checking for content availability.
- **User Impact**: Users are presented with an unhelpful page, leading to frustration and a perception of incomplete or broken data.
- **Suggested Direction**: Implement a pre-check for NTSB docket content. If the docket is not released, either disable the link, display a message indicating its status, or link to a more general NTSB search page for the incident number. This aligns with the "Dead Link Detection and Removal" issue (Issue 4) documented in `26_Apr_Observations.md`.

## 2. ~~Multiple Incidents Linking to the Same NTSB Page~~ — MISDIAGNOSIS (27 Apr)

- **Original Observation**: For the first 5 incidents displayed on the Boeing 747 page, all 'NTSB' and 'Details' links appeared to lead to the exact same NTSB page.
- **Correction**: Each of the 5 incidents has a distinct, correct NTSB docket URL (DCA26WA031, DCA26WA017, ENG25WA023, DCA25WA024, DCA24WA246). The data and template logic are correct — DB query confirmed each IncidentSource row has a unique `source_record_id`.
- **Actual Root Cause**: All 5 incidents are recent (2024–2026 event dates). NTSB routinely takes 12–24+ months to publish investigation dockets. These cases are legitimately in-progress, and their docket pages show "The docket for this investigation has not been released" — this is expected NTSB behavior, not a data or template bug.
- **Real Problem**: The app provides no UX signal that an NTSB docket link may point to an unreleased investigation. Users click through and land on an unhelpful page with no context.
- **Consolidated With Issue 1**: Both observations reduce to the same gap — see Issue 1 for the suggested direction.
