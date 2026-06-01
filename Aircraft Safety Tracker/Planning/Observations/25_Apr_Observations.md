# 25 Apr Observations

## 1. NTSB Model Mismatch on Incident Links

- **Observed issue:** When clicking on an NTSB link for a Boeing 707-321B incident (dated 2011-05-18), the link directed to `https://data.ntsb.gov/Docket/?NTSBNumber=DCA11PA075` which shows a Boeing 707-300, N707AR, not the correct Boeing 707-321B model.
- **Root cause hypothesis:** The aircraft model tagging logic for NTSB incidents may be too loose or relying on partial string matching, leading to incorrect model associations.
- **User impact:** Users are directed to the wrong incident details, reducing trust in the data accuracy.
- **Suggested direction:** Implement stricter model matching for NTSB links, ensuring the aircraft variant (e.g., 321B vs 300) is correctly identified and linked.

***

## 2. NTSB PDF Link Returns Error (DCA90MA019)

- **Observed issue:** Clicking the 'NTSB Docs' link for a Boeing 707-321B incident from 1990-01-25 directed to `https://data.ntsb.gov/carol-repgen/api/Aviation/ReportMain/GenerateNewestReport/DCA90MA019/pdf` and returned the error: `{ "Error": "The case with MKey 0 does not exist.", "ErrorCode": 0 }`.
- **Root cause hypothesis:** The NTSB case number (DCA90MA019) may be invalid, expired, or the report may have been removed from the NTSB database. The `MKey 0` error suggests the record does not exist or the link format is outdated.
- **User impact:** Users see an error page instead of the expected incident documentation, breaking the investigative workflow.
- **Suggested direction:**
  1. Validate NTSB links before displaying them, or provide a fallback mechanism (e.g., link to the general NTSB docket search for that case number).
  2. During ingestion, check if the NTSB API returns a valid response for the generated link; flag or skip links that return errors.
  3. Consider linking to the NTSB docket search page (`https://data.ntsb.gov/Docket/?NTSBNumber=<case>`) as a more stable fallback instead of the PDF direct link.

***

## 3. Homepage Manufacturer Search Missing Autocomplete / Fuzzy Dropdown

- **Observed issue:** The homepage search functionality for manufacturers (e.g., "Boeing", "Airbus") does not display all available models. The attached image shows "Boeing 727" as the only option for "Boeing", while many other Boeing models exist in the database. This suggests a lack of fuzzy search or autocomplete capabilities.
- **Root cause hypothesis:** The search input might be performing an exact match or a very limited prefix match, rather than a comprehensive fuzzy search across all available aircraft models. The previous version of the application had a more robust search.
- **User impact:** Users cannot easily discover or navigate to specific aircraft models, especially if they don't know the exact model name or if the model is not immediately visible. This hinders data exploration and usability.
- **Suggested direction:** Re-implement or enhance the search functionality to include fuzzy matching and an autocomplete dropdown that suggests relevant aircraft models as the user types. The search should cover all available models in the database.

***

## 4. Internal Server Error When Accessing Airline from List

- **Observed issue:** Attempting to access an airline from the list (e.g., by clicking on an airline link) results in an "Internal Server Error" page. The URL pattern observed is `http://localhost:5001/aircraft/635`, suggesting an issue with the `aircraft` endpoint when provided with an ID that might correspond to an airline or a malformed request.
- **Root cause hypothesis:** A recent change in the application's routing, data handling, or database queries related to aircraft or airline IDs might have introduced a regression. The error indicates a server-side issue preventing the page from rendering correctly.
- **User impact:** Users are unable to view details for specific airlines, breaking a core navigation and data exploration feature. This is a critical bug that needs immediate attention.
- **Suggested direction:**
  1. Identify the specific endpoint and backend logic responsible for handling requests to `/aircraft/<id>`.
  2. Review recent code changes related to this endpoint, especially those affecting database queries, data serialization, or error handling.
  3. Implement robust error logging and debugging to pinpoint the exact line of code causing the Internal Server Error.
  4. Develop a fix to ensure that airline details can be accessed without triggering a server error.