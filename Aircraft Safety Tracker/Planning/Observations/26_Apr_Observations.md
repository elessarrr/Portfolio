# 26 Apr Observations: Data Quality Issues and Solutions

This document outlines several data quality issues identified in the Aircraft Safety Tracker application and proposes systematic solutions for each.

---

## Issue 1: Model Sorting Logic

### Problem Statement
The current sorting behavior for aircraft models in the UI is inconsistent, leading to a non-intuitive display order. Specifically, a variant model like 'Boeing 747-400' appears before its base model 'Boeing 747'. This makes it difficult for users to quickly find and compare related aircraft models.

**Observed Behavior Example:**
- Boeing 747-400
- BOEING 747
- BOEING 747 - 400
- BOEING 747 - 406
- BOEING 747 - 409LCF

### Expected Behavior
Aircraft models should be sorted alphabetically, with base model names appearing before their variants. This ensures a logical and user-friendly ordering.

**Correct Sorting Order Example:**
- BOEING 747
- BOEING 747 - 400
- BOEING 747 - 406
- BOEING 747 - 409LCF
- Boeing 747-400

### Recommended Actions
Implement a custom sorting logic that prioritizes base model names over their variants. This can be achieved by:
1. **Parsing Model Names**: Extract the base model (e.g., "747" from "Boeing 747-400") and the variant suffix.
2. **Custom Sort Key**: Create a sort key that first sorts by the base model, then by the variant suffix.

### Implementation Details
The sorting logic should be applied at the database query level or within the application layer before rendering the UI.

**SQL Query Example (PostgreSQL with `regexp_replace`):**
```sql
SELECT model_name
FROM aircraft
ORDER BY
    CASE
        WHEN model_name ~ '^[A-Za-z]+ [0-9]+$' THEN 0 -- Base models like "Boeing 747"
        ELSE 1 -- Variants
    END,
    regexp_replace(model_name, '^([A-Za-z]+ [0-9]+).*', '\1'), -- Sort by base model part
    model_name; -- Then by full model name for variants
```

**Python/SQLAlchemy Example (within `app/routes.py` or a helper function):**
```python
from sqlalchemy import func, case, text

def get_sorted_aircraft_models(query_object):
    # This is a conceptual example and might need adjustment based on actual data structure
    # and performance considerations.
    return query_object.order_by(
        case(
            (Aircraft.model_name.regexp_match('^[A-Za-z]+ [0-9]+$'), 0), # Base models first
            else_=1
        ),
        func.regexp_replace(Aircraft.model_name, '^([A-Za-z]+ [0-9]+).*', r'\1'), # Sort by base
        Aircraft.model_name # Then by full name
    )
```

### Implementation Timeline & Complexity
- **Timeline**: 1-2 days
- **Complexity**: Medium (requires careful regex or string manipulation and testing across various model names)

### Testing Requirements
- **Unit Tests**: Verify the custom sorting function produces the correct order for a diverse set of model names (base, variants, different manufacturers).
- **Integration Tests**: Ensure the UI displays models in the expected sorted order on the homepage and any other relevant lists.

### Success Metrics
- All aircraft models are displayed in a consistent and logically sorted order.
- User feedback indicates improved navigability of aircraft lists.

---

## Issue 2: Capitalization Standardization

### Problem Statement
Inconsistent capitalization exists across manufacturer names and aircraft models in the database, leading to a fragmented and unprofessional user experience. For example, 'Boeing' might appear as 'BOEING' or 'boeing' in different records.

**Observed Inconsistencies:**
- 'BOEING' vs 'Boeing'
- 'AIRBUS' vs 'Airbus'
- 'BOEING 747' vs 'Boeing 747'

### Standard Format
All manufacturer names and aircraft models should adhere to **Title Case** (e.g., 'Boeing', 'Airbus', 'Boeing 747').

### Comprehensive List of Records Requiring Fixes
This list needs to be generated dynamically by querying the database for inconsistent entries.

**Example Query for Inconsistent Manufacturers:**
```sql
SELECT DISTINCT manufacturer
FROM aircraft
WHERE manufacturer IS NOT NULL
AND manufacturer <> INITCAP(manufacturer);
```

**Example Query for Inconsistent Model Names:**
```sql
SELECT DISTINCT model_name
FROM aircraft
WHERE model_name IS NOT NULL
AND model_name <> INITCAP(model_name);
```

### Database Update Scripts
A one-time migration script should be created to standardize existing data.

**SQL Update Example:**
```sql
UPDATE aircraft
SET manufacturer = INITCAP(manufacturer)
WHERE manufacturer IS NOT NULL
AND manufacturer <> INITCAP(manufacturer);

UPDATE aircraft
SET model_name = INITCAP(model_name)
WHERE model_name IS NOT NULL
AND model_name <> INITCAP(model_name);

-- Similar updates for AircraftVariant.variant_name and Incident.raw_model_variant
UPDATE aircraft_variant
SET variant_name = INITCAP(variant_name)
WHERE variant_name IS NOT NULL
AND variant_name <> INITCAP(variant_name);

UPDATE incident
SET raw_model_variant = INITCAP(raw_model_variant)
WHERE raw_model_variant IS NOT NULL
AND raw_model_variant <> INITCAP(raw_model_variant);
```

### Implementation Timeline & Complexity
- **Timeline**: 2-3 days (includes data analysis, script development, and thorough testing on a staging environment)
- **Complexity**: Medium (requires careful data manipulation and potential downtime for large datasets)

### Testing Requirements
- **Pre-update Data Snapshot**: Record a snapshot of affected data before running the script.
- **Post-update Verification**: Query the database to ensure all targeted fields are in Title Case.
- **UI Verification**: Confirm that the UI displays standardized capitalization across all relevant pages.

### Success Metrics
- All manufacturer and model names in the database and UI are consistently in Title Case.
- No new capitalization inconsistencies are introduced after the fix.

---

## Issue 3: Data Integrity in Series List

### Problem Statement
The "Series" list (likely referring to the manufacturer/base model grouping on the homepage) contains anomalous entries that are not valid aircraft models or manufacturers, such as standalone 'BOEING' entries and 'BOEING 75N1'. These entries indicate a lack of robust validation during data ingestion or processing.

**Observed Anomalies:**
- 'BOEING' (as a series, not a manufacturer)
- 'BOEING 75N1' (appears to be a malformed model name)
- 'Boeing 400' (potentially a generic entry without specific model)

### Investigation Findings
These non-aircraft model entries were likely introduced due to:
- **Loose Parsing**: Ingestion scripts might not be strictly validating parsed model names against a known list or pattern.
- **Incomplete Data**: Some source data might only provide a manufacturer without a specific model, leading to the manufacturer being treated as a "series".
- **Data Entry Errors**: Manual or automated errors during data import could introduce malformed entries.
- **Lack of Canonicalization**: Insufficient rules to transform raw input into a standardized format.

### Validation Rules to Prevent Future Issues
1. **Strict Model Name Pattern**: Implement regex-based validation for aircraft model names (e.g., `[Manufacturer] [Model Number]-[Variant]`).
2. **Manufacturer Lookup**: Validate that any manufacturer name exists in a predefined canonical list.
3. **Series Definition**: Clearly define what constitutes a valid "series" entry (e.g., only actual base models, not just manufacturers).
4. **Pre-Ingestion Hooks**: Add validation steps to the ingestion pipeline to reject or flag anomalous entries before they reach the database.

### Clear Criteria for Valid Aircraft Series Entry
A valid aircraft series entry should:
- Represent a distinct aircraft model or a well-defined family of models.
- Be associated with a known, canonical manufacturer.
- Not be a generic manufacturer name alone (unless it's a placeholder for unclassified models).
- Adhere to a consistent naming convention.

### Implementation Timeline & Complexity
- **Timeline**: 3-5 days (includes defining validation rules, updating ingestion scripts, and cleaning existing data)
- **Complexity**: High (requires changes to ingestion logic, potential data migration, and thorough testing)

### Testing Requirements
- **Unit Tests**: For new validation functions in the ingestion pipeline.
- **Integration Tests**: Run ingestion with known anomalous data to ensure rejection or proper flagging.
- **Regression Tests**: Verify that existing valid data is still ingested correctly.
- **UI Verification**: Confirm that the "Series" list only contains valid and correctly formatted entries.

### Success Metrics
- No anomalous entries appear in the "Series" list.
- All new data ingested adheres to the defined validation rules.
- Data integrity reports show zero invalid series entries.

---

## Issue 4: Dead Link Detection and Removal

### Problem Statement
The application contains external links (e.g., NTSB reports) that are dead (404, 500 errors, timeouts) or lead to pages indicating "docket not released". This degrades user experience and reduces the credibility of the data.

**Observed Issues:**
- NTSB PDF links returning `{ "Error": "The case with MKey 0 does not exist." }`
- NTSB docket pages stating "The docket for this investigation has not been released."
- General HTTP 404/500 errors or timeouts for external URLs.

### Systematic Link Validation Process
A dedicated agent or background job should periodically validate all external links stored in the `IncidentSource` table.

### Detailed Agent Prompt for Link Validation
```markdown
**Agent Name**: LinkValidator
**Purpose**: Systematically validate external URLs in the `IncidentSource` table.

**Input**:
- List of URLs from `IncidentSource.source_url` and `IncidentSource.report_url`.

**Process**:
1.  **HTTP Status Code Check**:
    -   Perform a HEAD request for `source_url` to check for 404, 500, or timeout errors.
    -   Perform a GET request for `report_url` (especially for PDFs) to check status codes.
    -   **Timeout**: Consider a link "dead" if it times out after 10 seconds.
2.  **Content Validation (for `report_url` / NTSB dockets)**:
    -   If the `report_url` is an NTSB docket page, perform a GET request and check the response body for specific phrases like "The docket for this investigation has not been released." or `{ "Error": "The case with MKey 0 does not exist." }`.
    -   Flag such links as "Content Invalid".
3.  **Rate Limiting**:
    -   Implement a delay of at least 1 second between requests to the same domain to avoid overwhelming external servers.
    -   Use a configurable global rate limit (e.g., 5 requests per second).
4.  **Error Handling**:
    -   Distinguish between network errors (timeout, connection refused), HTTP errors (4xx, 5xx), and content errors.

**Output Format**:
Generate a CSV report with the following columns:
`URL, HTTP_Status, Error_Type, Content_Issue, Recommended_Action, IncidentSource_ID`

-   `URL`: The validated URL.
-   `HTTP_Status`: HTTP status code (e.g., 200, 404, 500, TIMEOUT).
-   `Error_Type`: Categorization (e.g., 'HTTP_ERROR', 'NETWORK_ERROR', 'CONTENT_ERROR').
-   `Content_Issue`: Specific content issue (e.g., 'Docket Not Released', 'API Error Message').
-   `Recommended_Action`: 'Remove Link', 'Investigate Manually', 'Update URL'.
-   `IncidentSource_ID`: The ID of the `IncidentSource` record.

**Reporting Structure**:
-   **Priority 1 (High)**: HTTP 404, 500, TIMEOUT errors. Recommended Action: 'Remove Link'.
-   **Priority 2 (Medium)**: Content Invalid (e.g., "docket not released"). Recommended Action: 'Investigate Manually' or 'Update URL' (if a general search link is available).
-   **Priority 3 (Low)**: Other non-200 but non-critical status codes (e.g., 3xx redirects that don't resolve). Recommended Action: 'Investigate Manually'.

### Database Queries for Links
```sql
-- Identify all external links for validation
SELECT id, source_url, report_url
FROM incident_source
WHERE source_url IS NOT NULL OR report_url IS NOT NULL;
```

### Removal Protocol for Confirmed Dead Links
1.  **Automated Flagging**: The LinkValidator agent flags dead links in the `IncidentSource` table (e.g., `is_valid = FALSE`, `validation_error = '...'`).
2.  **Review & Approval**: A human reviewer (or a more advanced agent) reviews flagged links.
3.  **Soft Deletion/Archiving**: Instead of hard deleting, set a `status = 'dead'` or `is_active = FALSE` flag on the `IncidentSource` record. This preserves historical data while preventing the link from being displayed.
4.  **UI Update**: The UI should filter out or visually indicate inactive/dead links.

### Implementation Timeline & Complexity
-   **Timeline**: 5-7 days (includes agent development, testing, and initial data cleanup)
-   **Complexity**: High (requires external HTTP requests, robust error handling, and careful state management)

### Testing Requirements
-   **Unit Tests**: For HTTP request logic, content parsing, and rate limiting.
-   **Integration Tests**: Test against known good and known bad URLs (mock external services if necessary).
-   **End-to-End Tests**: Verify that dead links are correctly flagged and not displayed in the UI.

### Success Metrics
-   Reduction in reported dead links by users.
-   Automated reports show a high accuracy in identifying dead/invalid links.
-   UI consistently displays only valid and accessible external links.

---

## Summary and Priority Ranking

| Issue | Priority | Implementation Timeline | Complexity | Success Metrics |
|---|---|---|---|---|
| 1. Model Sorting Logic | High | 1-2 days | Medium | Consistent, logical model sorting in UI. |
| 2. Capitalization Standardization | High | 2-3 days | Medium | All manufacturer/model names in Title Case. |
| 3. Data Integrity in Series List | High | 3-5 days | High | No anomalous entries in Series list; new data validated. |
| 4. Dead Link Detection and Removal | Medium | 5-7 days | High | Significant reduction in dead links; UI shows valid links. |
