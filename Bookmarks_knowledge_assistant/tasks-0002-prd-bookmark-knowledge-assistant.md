# Task List: Bookmark Knowledge Assistant

**PRD Reference:** `0002-prd-bookmark-knowledge-assistant.md`  
**Created:** January 2025

---

## Relevant Files

- `app.py` - Main Streamlit application entry point
- `src/bookmark_import.py` - Chrome bookmark file detection and parsing logic
- `src/bookmark_import_test.py` - Unit tests for bookmark import
- `src/content_fetcher.py` - HTTP fetching and content extraction using readability
- `src/content_fetcher_test.py` - Unit tests for content fetching
- `src/database.py` - SQLite schema, connection, and CRUD operations
- `src/database_test.py` - Unit tests for database operations
- `src/embeddings.py` - Sentence-transformers embedding generation
- `src/embeddings_test.py` - Unit tests for embedding generation
- `src/vector_store.py` - ChromaDB integration for vector storage and search
- `src/vector_store_test.py` - Unit tests for vector store
- `src/search.py` - Hybrid search combining full-text and semantic search
- `src/search_test.py` - Unit tests for search functionality
- `src/llm_client.py` - OpenAI/Anthropic API abstraction layer
- `src/llm_client_test.py` - Unit tests for LLM client
- `src/rag.py` - RAG pipeline: retrieve chunks, format prompt, generate cited answer
- `src/rag_test.py` - Unit tests for RAG pipeline
- `src/config.py` - Settings management (API keys, preferences)
- `src/config_test.py` - Unit tests for config
- `pages/chat.py` - Streamlit chat interface page
- `pages/library.py` - Streamlit bookmark library view page
- `pages/settings.py` - Streamlit settings page
- `requirements.txt` - Python dependencies
- `README.md` - Setup instructions and documentation
- `.env.example` - Example environment variables file

### Notes

- Unit tests should be placed alongside the code files they test (e.g., `database.py` and `database_test.py` in the same directory).
- Use `pytest` to run tests: `pytest src/` or `pytest src/database_test.py` for specific files.
- Streamlit pages in `pages/` folder are auto-detected by Streamlit's multipage app feature.

---

## Tasks

- [ ] 1.0 Project Setup & Database Schema
  - [ ] 1.1 Create project directory structure (`src/`, `pages/`, `data/`)
  - [ ] 1.2 Create `requirements.txt` with initial dependencies: `streamlit`, `sqlite3` (built-in), `requests`, `beautifulsoup4`, `readability-lxml`, `sentence-transformers`, `chromadb`, `openai`, `anthropic`
  - [ ] 1.3 Create virtual environment setup instructions in README
  - [ ] 1.4 Design SQLite schema with tables: `bookmarks` (id, url, title, folder_path, date_added, fetch_status, content, fetched_at)
  - [ ] 1.5 Implement `src/database.py` with functions: `init_db()`, `insert_bookmark()`, `get_all_bookmarks()`, `get_bookmark_by_url()`, `update_bookmark_content()`, `update_fetch_status()`
  - [ ] 1.6 Write unit tests for database CRUD operations in `src/database_test.py`
  - [ ] 1.7 Create `.env.example` with placeholder for `OPENAI_API_KEY` and `ANTHROPIC_API_KEY`

- [ ] 2.0 Chrome Bookmark Import System
  - [ ] 2.1 Implement OS detection function to locate Chrome bookmarks file (macOS, Windows, Linux paths)
  - [ ] 2.2 Implement JSON parser to read Chrome's `Bookmarks` file format
  - [ ] 2.3 Create recursive function to traverse bookmark tree and extract: url, title, folder path, date_added
  - [ ] 2.4 Implement folder filtering: return list of available folders, allow user to select which to import
  - [ ] 2.5 Implement duplicate detection: check if URL already exists in database before inserting
  - [ ] 2.6 Create `import_bookmarks(folder_filter=None)` main function that orchestrates the import
  - [ ] 2.7 Write unit tests with sample Chrome bookmark JSON fixtures in `src/bookmark_import_test.py`

- [ ] 3.0 Content Fetching & Extraction Pipeline
  - [ ] 3.1 Implement `fetch_url(url)` function with timeout handling (10s), user-agent header, and error catching
  - [ ] 3.2 Implement `extract_content(html)` using `readability-lxml` to get main article text
  - [ ] 3.3 Implement fallback extraction using BeautifulSoup if readability fails (strip scripts, get text)
  - [ ] 3.4 Create status enum: `PENDING`, `SUCCESS`, `FAILED_TIMEOUT`, `FAILED_404`, `FAILED_PAYWALL`, `FAILED_OTHER`
  - [ ] 3.5 Implement `fetch_and_store(bookmark_id)` that fetches, extracts, and updates database
  - [ ] 3.6 Implement `fetch_all_pending()` batch function with progress callback for UI updates
  - [ ] 3.7 Add paywall detection heuristic (check for common paywall indicators in HTML)
  - [ ] 3.8 Write unit tests with mocked HTTP responses in `src/content_fetcher_test.py`

- [ ] 4.0 Search & Retrieval System (Embeddings + Hybrid Search)
  - [ ] 4.1 Implement `src/embeddings.py` with `get_embedding(text)` using sentence-transformers model (`all-MiniLM-L6-v2`)
  - [ ] 4.2 Implement text chunking function: split content into ~500 token chunks with overlap
  - [ ] 4.3 Set up ChromaDB local persistent storage in `data/chroma/`
  - [ ] 4.4 Implement `index_bookmark(bookmark_id)` that chunks content, generates embeddings, stores in ChromaDB with metadata (bookmark_id, url, title)
  - [ ] 4.5 Implement `index_all_unindexed()` batch function to index all bookmarks with SUCCESS status
  - [ ] 4.6 Implement `semantic_search(query, top_k=10)` using ChromaDB similarity search
  - [ ] 4.7 Implement `keyword_search(query, top_k=10)` using SQLite FTS5 full-text search
  - [ ] 4.8 Implement `hybrid_search(query, top_k=15)` that combines and re-ranks results from both methods
  - [ ] 4.9 Write unit tests for embedding generation and search in respective test files

- [ ] 5.0 LLM Integration with Citations
  - [ ] 5.1 Create `src/llm_client.py` with abstract interface: `generate(prompt, system_message=None)`
  - [ ] 5.2 Implement `OpenAIClient` class using `openai` SDK (model: `gpt-4o-mini`)
  - [ ] 5.3 Implement `AnthropicClient` class using `anthropic` SDK (model: `claude-3-haiku`)
  - [ ] 5.4 Implement `get_client(provider)` factory function that returns appropriate client based on config
  - [ ] 5.5 Create RAG prompt template that instructs LLM to cite sources using [1], [2] format
  - [ ] 5.6 Implement `generate_answer(query, chunks)` in `src/rag.py` that: formats context with source numbers, calls LLM, parses response
  - [ ] 5.7 Implement citation extraction: parse [n] references from response, map to source bookmarks
  - [ ] 5.8 Format final response with clickable source links and "Sources" section
  - [ ] 5.9 Handle edge case: no relevant chunks found → return "No relevant bookmarks found" message
  - [ ] 5.10 Write unit tests with mocked LLM responses in `src/rag_test.py`

- [ ] 6.0 Streamlit Web Interface
  - [ ] 6.1 Create `app.py` main entry point with sidebar navigation (Chat, Library, Settings)
  - [ ] 6.2 Implement `pages/chat.py`: text input for query, submit button, chat history display
  - [ ] 6.3 Add loading spinner during search and LLM generation
  - [ ] 6.4 Display AI response with formatted citations (numbered references as links)
  - [ ] 6.5 Display expandable "Sources" section showing referenced bookmarks with titles and URLs
  - [ ] 6.6 Implement `pages/library.py`: table view of all bookmarks with columns (title, url, folder, status)
  - [ ] 6.7 Add status badges/icons (✓ success, ✗ failed, ⏳ pending) in library view
  - [ ] 6.8 Add "Import Bookmarks" button that triggers import flow with folder selection
  - [ ] 6.9 Add "Fetch All" button with progress bar for bulk content fetching
  - [ ] 6.10 Add "Re-fetch" button per bookmark row for individual refresh
  - [ ] 6.11 Implement `pages/settings.py`: form inputs for OpenAI and Anthropic API keys
  - [ ] 6.12 Add provider selection dropdown (OpenAI / Anthropic)
  - [ ] 6.13 Add "Test API Key" button that validates key and shows success/error
  - [ ] 6.14 Persist settings to local config file on save

- [ ] 7.0 Configuration & Settings Management
  - [ ] 7.1 Create `src/config.py` with `Config` class to manage settings
  - [ ] 7.2 Implement settings storage in `data/config.json` (API keys, selected provider)
  - [ ] 7.3 Implement `load_config()` and `save_config()` functions
  - [ ] 7.4 Add API key validation functions: `validate_openai_key()`, `validate_anthropic_key()`
  - [ ] 7.5 Ensure API keys are never logged or exposed in error messages
  - [ ] 7.6 Write unit tests for config load/save in `src/config_test.py`

- [ ] 8.0 Documentation & Launch Prep
  - [ ] 8.1 Write comprehensive README.md with: project description, features, installation steps, usage guide
  - [ ] 8.2 Add screenshots/GIFs of the UI in action
  - [ ] 8.3 Document supported platforms (macOS, Windows, Linux) and Chrome bookmark locations
  - [ ] 8.4 Add troubleshooting section for common issues (Chrome not found, API key errors, etc.)
  - [ ] 8.5 Create LICENSE file (MIT recommended for portfolio project)
  - [ ] 8.6 Add `.gitignore` for `data/`, `.env`, `__pycache__/`, `.venv/`
  - [ ] 8.7 Test full flow end-to-end: install → import → fetch → query → get cited answer
  - [ ] 8.8 Create GitHub repository with appropriate topics/tags
  - [ ] 8.9 Draft LinkedIn launch post highlighting problem solved and inviting feedback

---

## Implementation Order Recommendation

For a junior developer, recommended order:

1. **Tasks 1.0** → Get project structure and database working
2. **Tasks 2.0** → Bookmark import (can test independently)
3. **Tasks 3.0** → Content fetching (can test independently)
4. **Tasks 7.0** → Config management (needed before LLM)
5. **Tasks 4.0** → Search system (most complex, take time here)
6. **Tasks 5.0** → LLM integration (depends on 4.0 and 7.0)
7. **Tasks 6.0** → UI (can start early with stubs, complete after backend)
8. **Tasks 8.0** → Documentation (do alongside development)

---

**Total Estimated Time:** 10-15 hours for experienced developer, 20-30 hours for junior developer
