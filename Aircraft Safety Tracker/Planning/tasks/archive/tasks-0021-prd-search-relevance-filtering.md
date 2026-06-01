## Status

- Overall Progress: 🟢 `100%` (All tasks complete)
- Execution State: ✅ Implementation complete, ✅ dry-run verified, ✅ tests passing

## Relevant Files

- `app/services/web_search.py` - Contains the updated strict query formatting, HTML fetching, text validation, and metadata extraction logic.
- `app/ingestion/cli.py` - Handles the `MEDIA_NO_RESULT` negative cache flag and saves extracted metadata (title/snippet) into the `source_data` JSON field.
- `tests/test_web_search_service.py` - Unit tests for the HTML validation and snippet extraction functions.

### Notes

- We will use the existing `beautifulsoup4` dependency for safe and robust HTML tag stripping.
- The `MEDIA_NO_RESULT` flag should be implemented as an `IncidentSource` record with `is_active=False` so it doesn't affect the UI but prevents the CLI job from re-querying it.

## Tasks

- [x] 1.0 Implement Strict Search Query Formatting
  - [x] 1.1 Update `_build_aviation_herald_query` to wrap `event_id` and `registration` in exact-match quotes.
  - [x] 1.2 Update `_build_news_wire_query` to wrap `event_id` and `registration` in exact-match quotes.
  - [x] 1.3 Update `_build_general_query` to wrap `event_id` and `registration` in exact-match quotes.
- [x] 2.0 Implement HTML Content Fetching and Text Validation
  - [x] 2.1 Add a `snippet` field to the `SearchResult` dataclass.
  - [x] 2.2 Create a `_fetch_and_validate_html(url: str, match_keywords: List[str]) -> Tuple[bool, Optional[str], Optional[str], Optional[str]]` function returning `(is_valid, title, snippet, error_detail)`.
  - [x] 2.3 Implement the HTTP GET request with a 10-second timeout and browser User-Agent inside the new function.
  - [x] 2.4 Use BeautifulSoup to extract text from the HTML body and strip tags.
  - [x] 2.5 Verify if any of the `match_keywords` exist in the extracted text.
- [x] 3.0 Implement Metadata Extraction (Title & Snippet)
  - [x] 3.1 Inside `_fetch_and_validate_html`, extract the `<title>` tag if validation passes.
  - [x] 3.2 Find the index of the matched keyword in the stripped text, and extract a substring of ~150-200 characters around it to serve as the `snippet`.
- [x] 4.0 End-to-End Integration in WebSearchService
  - [x] 4.1 Update `search_tiered` to pass `event_id` and `registration` as keywords to the validation flow.
  - [x] 4.2 Replace the old `validate_url` call in `search_tiered` with the new `_fetch_and_validate_html` call.
  - [x] 4.3 Populate the `title` and `snippet` fields on the `SearchResult` object.
- [x] 5.0 Implement Negative Caching ("No Result" Flagging)
  - [x] 5.1 In `app/ingestion/cli.py` (`enrich-wa-incidents`), update the target query to exclude incidents that already have a `MEDIA_NO_RESULT` record.
  - [x] 5.2 If no valid articles are found for an incident, create a new `IncidentSource` with `source_name='MEDIA_NO_RESULT'`, `source_record_id=f"{event_id}:no_result"`, and `is_active=False`.
  - [x] 5.3 If a valid article is found, save `title` and `snippet` into the `source_data` JSON for the `MEDIA` source.
- [x] 6.0 Testing and Cleanup
  - [x] 6.1 Update `tasks-03052026-wa-suppression-and-enrichment.md` to note the dependency on PRD-0021.
  - [x] 6.2 Test `enrich-wa-incidents` via `--dry-run` to ensure targets are identified correctly.
  - [x] 6.3 Run tests to verify the pipeline doesn't break existing functionality.
