# 0015-prd-manufacturer-search-autocomplete

## 1. Introduction/Overview

The Aircraft Safety Tracker's main search input currently lacks an autocomplete dropdown. When a user types an airplane manufacturer or model name, no suggestions appear, forcing users to guess exact strings or rely on the submit action. Earlier versions of the app featured a fuzzy-search-like autocomplete dropdown that significantly improved discoverability. This PRD outlines the plan to re-introduce this autocomplete functionality to improve user experience and search efficiency.

## 2. Goals

- **Restore Autocomplete UX:** Re-introduce a dropdown list of suggestions that appears as users type in the search input.
- **Improve Discoverability:** Allow users to find aircraft by typing partial names (e.g., "737" finds "Boeing 737").
- **Maintain Performance:** Ensure the autocomplete query is fast and doesn't degrade page load times.

## 3. User Stories

- **As a user**, I want to see suggestions as I type so I can quickly find the aircraft model I'm looking for without knowing the exact string.
- **As a user**, I want to be able to type partial matches (like "737") and see relevant suggestions (like "Boeing 737-800") so that I don't have to guess exact model names.
- **As a user**, I want to click a suggestion to be taken directly to that aircraft's detail page.

## 4. Functional Requirements

1. **Autocomplete Endpoint:** Create a new backend API endpoint (e.g., `/api/search/autocomplete?q=<query>`) that accepts a query string and returns a JSON list of up to 5 matching aircraft models.
2. **Search Coverage:** The autocomplete should search aircraft manufacturer and model names only (e.g., "Boeing 747", "Airbus A320"). Airline/operator names are out of scope.
3. **Matching Logic:** The search should use substring/fuzzy matching. For example, typing "737" should return results containing "737" anywhere in the name (e.g., "Boeing 737-800", "Boeing 737 MAX 9").
4. **Frontend Integration:**
   - The search input field in `index.html` should trigger the autocomplete on `keyup` or `input` events.
   - A dropdown list should appear below the input showing up to 5 matching suggestions.
   - Each suggestion should be clickable and navigate to the corresponding aircraft detail page.
5. **UX Details:**
   - The dropdown should appear only when there are matching results and the user has typed at least 2 characters.
   - The dropdown should disappear when the user clicks outside or presses Escape.
   - Styling should be clean and integrate with the existing Tailwind CSS design.

## 5. Non-Goals (Out of Scope)

- Searching airline or operator names.
- Showing more than 5 results in the dropdown.
- Adding autocomplete to any other search fields (e.g., the incidents page filters).

## 6. Design Considerations

- **Dropdown Styling:** The autocomplete dropdown should visually match the existing search input style, with a clean border, shadow, and hover states for suggestions.
- **Performance:** Consider adding a small debounce (e.g., 200ms) to the input event to avoid excessive API calls while typing.

## 7. Technical Considerations

- **Backend:** The existing search infrastructure (PostgreSQL with `pg_trgm` for fuzzy matching) can be leveraged. A new lightweight endpoint in `app/routes.py` can handle the autocomplete queries.
- **Frontend:** Vanilla JavaScript (in `main.js`) or HTMX can be used to handle the input events and dropdown rendering. No major frontend framework changes are required.
- **Database Query:** Use a simple `ILIKE` or `pg_trgm` query against the `Aircraft` model's `full_name` or `make_model` columns, limited to 5 results.

## 8. Success Metrics

- Typing at least 2 characters in the search input shows a dropdown with up to 5 matching aircraft suggestions within 200ms.
- Clicking a suggestion navigates to the correct aircraft detail page.
- The dropdown disappears correctly on Escape or click-outside.

## 9. Open Questions

- None at this time.

