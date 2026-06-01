# PRD: Search Relevance & Filtering for Incident Enrichment

## 1. Introduction/Overview
During the enrichment of WA-coded NTSB incidents with press articles via SerpAPI (and Google Custom Search), a critical relevance issue was identified. Search engines frequently return false positives due to "fuzzy matching," where the incident's event ID or registration appears in unrelated sidebars, generic pages, or recommended links. For example, a query for incident `MIA88WA207` returned Aviation Herald articles about completely unrelated Boeing 757 and Airbus A320 incidents. 

This PRD outlines the requirements for implementing strict search query formatting, post-fetch HTML text validation, metadata extraction, and negative caching ("No Result" flagging). These measures will ensure that only highly relevant press articles are attached to incidents, improving data trust and preventing the exhaustion of search API quotas.

## 2. Goals
* **Eliminate False Positives:** Ensure media links attached to an incident are factually related to that specific incident.
* **Optimize API Usage:** Stop wasting API quotas on repeated queries for incidents that have no relevant press coverage.
* **Aid Verification:** Provide useful context (metadata like article title and snippets) to aid in manual verification and eventual UI display.

## 3. User Stories
* **As an end-user**, I want the media links attached to an incident to point to actual articles about that specific incident, so I can trust the provided data.
* **As an administrator/reviewer**, I want to see the article title and snippet alongside the URL, so I can quickly verify its relevance without needing to open every link.
* **As the system**, I want to permanently record when a search yields no valid results for an incident, so I don't repeatedly exhaust daily search API quotas on dead ends.

## 4. Functional Requirements
1. **Strict Search Query Formatting:** The search module (`app.services.web_search`) must wrap the `event_id` (and potentially `registration` if available) in exact-match quotes (e.g., `"MIA88WA207"`) when constructing the query sent to SerpAPI/Google.
2. **HTML Content Verification:** Before saving a URL as a media source, the system must download the target HTML page.
3. **Relevance Check:** The system must strip HTML tags and verify that the exact `event_id` (or `registration` string) is present within the visible text of the article.
4. **Metadata Extraction:** Upon successful HTML verification, the system must extract the page `<title>` and a short contextual text snippet (e.g., 150-200 characters surrounding the matched keyword).
5. **Metadata Storage:** The extracted title and snippet must be saved in a structured format (e.g., as JSON) associated with the `MEDIA` source record in the database.
6. **"No Result" Flagging (Negative Cache):** If a search returns results but none pass the HTML relevance check (or if the search simply returns 0 results), the system must create a specific record or flag (e.g., `source_name="MEDIA_NO_RESULT"`) indicating "No Result" for this incident. This prevents the enrichment background job from retrying the same incident on subsequent runs.

## 5. Non-Goals (Out of Scope)
* **LLM Scoring:** Using Large Language Models (like DeepSeek or Gemini) to score or summarize article relevance.
* **Semantic NLP:** Complex natural language processing to understand the semantic meaning of the article text.
* **Infinite Retries:** Automatically retrying failed URL fetches beyond standard, brief HTTP timeout/retry mechanisms.

## 6. Design Considerations (Optional)
* **UI Updates:** The incident display UI might be updated in a later phase to display the extracted title/snippet on hover or in an expanded view. For now, this data is primarily for backend storage and manual admin review.
* **Negative Cache Representation:** Consider how the "No Result" state is represented in the `IncidentSource` table. Saving a dummy record with `source_name="MEDIA_NO_RESULT"` and `is_active=False` ensures the query can easily exclude it in the future without altering the database schema.

## 7. Technical Considerations (Optional)
* **HTML Parsing:** Use `BeautifulSoup` (`bs4`) or a similar lightweight library to strip HTML tags and extract text/titles cleanly.
* **Performance & Timeouts:** Downloading and parsing HTML for every candidate URL will slow down the enrichment script. The script should implement strict timeouts (e.g., 5-10 seconds) to prevent hanging on slow servers.
* **Scraping Protections:** Some news sites (e.g., Reuters, AP News) may block simple HTTP requests or return CAPTCHAs. Implement a standard browser `User-Agent` header. If a fetch fails due to a 403 or CAPTCHA, it should be gracefully handled (e.g., logged and skipped).

## 8. Success Metrics
* **0% False Positives:** Achieved in a manual random sampling of 50 newly enriched WA incidents.
* **Quota Efficiency:** A significant reduction in wasted daily search API queries, monitored via API dashboards, as the backlog of "un-enrichable" incidents is properly flagged and skipped.

## 9. Open Questions
* **Storage Schema:** What is the exact database schema field we will use to store the extracted JSON metadata? (Does `IncidentSource` have an `extra_data` JSON column, or should we append it to an existing text field/description?)
* **Negative Cache Expiry:** Should the "No Result" negative cache expire after a certain period (e.g., 6 months to catch newly published retrospective articles), or should it be permanent?