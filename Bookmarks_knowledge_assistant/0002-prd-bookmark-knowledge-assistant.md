# Product Requirements Document: Bookmark Knowledge Assistant

**Project ID:** 0002  
**Created:** January 2025  
**Author:** Raj

---

## 1. Introduction/Overview

### Problem Statement
People accumulate hundreds of browser bookmarks over years - articles, tutorials, advice, references - with the intention of "reading later." In practice, they never return to them, and when facing a decision or question, they can't recall which bookmark might have relevant advice. The knowledge is saved but effectively lost.

### Solution
A local web application that imports Chrome bookmarks, fetches and stores the full content of each page, and allows users to ask natural language questions. The tool searches across all bookmark content, retrieves relevant passages, and provides AI-synthesized answers with citations back to the original bookmarks for fact-checking.

### Goal
Enable users to unlock the value of their accumulated bookmarks by querying them as a personal knowledge base, getting actionable advice with verifiable sources.

---

## 2. Goals

### Primary Goals
1. **Zero-friction import:** One-click import of Chrome bookmarks (no manual CSV exports)
2. **Full content preservation:** Store complete page content, not summaries, so nothing is lost
3. **Cited answers:** Every AI response must reference specific bookmarks so users can verify
4. **Local-first:** Runs on user's machine, no account required, content stays private

### Secondary Goals
1. Demonstrate product-building skills for portfolio
2. Open-source for community contribution and visibility
3. Architecture that supports future enhancements (Safari, Ollama, etc.)

---

## 3. User Stories

### Primary User: Bookmark Hoarder
**As someone with hundreds of unread bookmarks,**  
I want to ask questions and get answers synthesized from my saved articles,  
So that I can finally extract value from content I saved but never read.

### Primary User: Decision Maker
**As someone facing a specific decision,**  
I want to see what my bookmarks say for and against my planned approach,  
So that I can make a more informed choice using advice I previously trusted enough to save.

### Secondary User: Researcher
**As someone who bookmarks articles on a topic over time,**  
I want to query "what do my bookmarks say about X,"  
So that I can get a synthesized view across multiple sources without re-reading everything.

---

## 4. Functional Requirements

### FR-1: Bookmark Import (MUST HAVE)
**The system must import bookmarks from Chrome automatically.**

- **FR-1.1:** Detect and read Chrome's bookmarks file from standard OS locations (macOS, Windows, Linux)
- **FR-1.2:** Parse bookmark structure including folders, names, URLs, and date added
- **FR-1.3:** Display import preview showing bookmark count and folder structure
- **FR-1.4:** Allow user to select specific folders to import (not forced to import all)
- **FR-1.5:** Handle duplicate URLs gracefully (skip or update)

### FR-2: Content Fetching (MUST HAVE)
**The system must fetch and store full page content for each bookmark.**

- **FR-2.1:** Fetch page content via HTTP request for each imported URL
- **FR-2.2:** Extract main content (strip navigation, ads, footers) using readability algorithm
- **FR-2.3:** Store raw text content associated with each bookmark
- **FR-2.4:** Handle failures gracefully (dead links, paywalls, timeouts) with clear status indicators
- **FR-2.5:** Show progress during bulk fetching with ability to pause/resume
- **FR-2.6:** Support re-fetching individual bookmarks to update stale content

### FR-3: Content Storage (MUST HAVE)
**The system must store bookmark metadata and content locally.**

- **FR-3.1:** Store in local SQLite database (portable, no setup required)
- **FR-3.2:** Store: URL, title, folder path, date added, fetch status, full text content
- **FR-3.3:** Create text embeddings for semantic search using sentence-transformers
- **FR-3.4:** Store embeddings in vector-capable SQLite extension (sqlite-vss) or ChromaDB

### FR-4: Search and Retrieval (MUST HAVE)
**The system must find relevant bookmarks for a given query.**

- **FR-4.1:** Support full-text keyword search across all bookmark content
- **FR-4.2:** Support semantic/vector search for conceptual matching
- **FR-4.3:** Combine both search types for hybrid retrieval
- **FR-4.4:** Return ranked list of relevant text chunks with source bookmark metadata
- **FR-4.5:** Retrieve sufficient context (e.g., top 10-20 chunks) for LLM synthesis

### FR-5: AI-Synthesized Answers (MUST HAVE)
**The system must provide natural language answers with citations.**

- **FR-5.1:** Send retrieved chunks + user query to LLM (OpenAI or Anthropic API)
- **FR-5.2:** Generate synthesized answer addressing the user's question
- **FR-5.3:** Every claim in the answer must cite the source bookmark(s)
- **FR-5.4:** Citations formatted as clickable links to original bookmark URLs
- **FR-5.5:** Display "Sources" section listing all bookmarks referenced in the answer
- **FR-5.6:** If no relevant bookmarks found, clearly state this rather than hallucinating

### FR-6: User Interface (MUST HAVE)
**The system must provide a simple, usable web interface.**

- **FR-6.1:** Clean chat-style interface for asking questions
- **FR-6.2:** Bookmark library view showing all imported bookmarks with status
- **FR-6.3:** Import wizard for initial setup and adding new bookmarks
- **FR-6.4:** Settings page for API key configuration
- **FR-6.5:** Responsive design (works on desktop browsers)

### FR-7: Configuration (MUST HAVE)
**The system must allow users to configure their LLM provider.**

- **FR-7.1:** Settings UI to enter OpenAI API key
- **FR-7.2:** Settings UI to enter Anthropic API key
- **FR-7.3:** Dropdown to select which provider to use
- **FR-7.4:** Validate API key on save and show clear error if invalid
- **FR-7.5:** Store API keys locally (not transmitted anywhere except to provider)

---

## 5. Non-Goals (Out of Scope)

### Explicitly NOT Building:
1. **Safari support** - Future enhancement, not MVP
2. **Ollama/local LLM support** - Architecture should allow it, but not implementing now
3. **Browser extension** - Standalone app only; no live bookmark sync
4. **Multi-user/accounts** - Single user, local only
5. **Cloud sync** - Everything stays on local machine
6. **Mobile app** - Desktop browser only
7. **Automatic bookmark organization/tagging** - Query only, no reorganization
8. **Bookmark recommendations** - Not suggesting new content to save
9. **PDF/document support** - Web pages only for MVP
10. **Scheduled re-fetching** - Manual refresh only

---

## 6. Design Considerations

### Design Philosophy
**Simple, functional, developer-friendly.** This is a utility, not a consumer product. Clean but not over-designed.

### UI Layout:
1. **Left sidebar:** Navigation (Chat, Library, Settings)
2. **Main area:** Context-dependent (chat interface, bookmark list, or settings form)
3. **Chat view:** Message history with clear distinction between user queries and AI responses

### Visual Style:
- Minimal, light theme (dark theme nice-to-have)
- System fonts for speed
- Clear visual hierarchy for citations (e.g., numbered references, expandable source cards)

---

## 7. Technical Considerations

### Technology Stack

**Backend:**
- Python (FastAPI or Flask)
- SQLite for metadata and content storage
- ChromaDB or sqlite-vss for vector embeddings
- sentence-transformers for local embedding generation
- OpenAI/Anthropic SDK for LLM calls

**Frontend:**
- Simple HTML/CSS/JavaScript (no heavy framework needed)
- Alternatively: Streamlit or Gradio for faster prototyping (acceptable for portfolio piece)

**Packaging:**
- Single command to run: `python app.py` or `pip install bookmark-assistant && bookmark-assistant`
- Clear README with setup instructions

### Architecture:

```
┌─────────────────────────────────────────────────────┐
│                   Local Web UI                       │
│              (localhost:8000)                        │
└─────────────────┬───────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────┐
│                 FastAPI Backend                      │
├─────────────────────────────────────────────────────┤
│  /import - Chrome bookmark import                    │
│  /fetch - Content fetching                          │
│  /query - Search + LLM synthesis                    │
│  /bookmarks - Library CRUD                          │
│  /settings - API key management                     │
└───────┬─────────────────┬─────────────────┬─────────┘
        │                 │                 │
┌───────▼──────┐ ┌────────▼───────┐ ┌───────▼────────┐
│   SQLite     │ │   ChromaDB     │ │  OpenAI/       │
│  (metadata,  │ │  (vectors)     │ │  Anthropic API │
│   content)   │ │                │ │                │
└──────────────┘ └────────────────┘ └────────────────┘
```

### Chrome Bookmark Locations:
- **macOS:** `~/Library/Application Support/Google/Chrome/Default/Bookmarks`
- **Windows:** `%LOCALAPPDATA%\Google\Chrome\User Data\Default\Bookmarks`
- **Linux:** `~/.config/google-chrome/Default/Bookmarks`

### Content Extraction:
- Use `newspaper3k` or `readability-lxml` for article extraction
- Fallback to BeautifulSoup with basic text extraction if those fail

---

## 8. Success Metrics

### For Portfolio/Open Source:
1. **GitHub stars:** 100+ within first month of launch
2. **Usability:** Can go from `git clone` to asking first question in under 5 minutes
3. **LinkedIn post engagement:** 50+ reactions on launch post

### For Personal Use:
4. **Actually useful:** You (Raj) use it at least once per week
5. **Works reliably:** 90%+ of bookmarks successfully fetched and indexed

---

## 9. Open Questions

1. **Embedding model:** Use OpenAI embeddings (requires API) or local sentence-transformers (free, slower)?
   - *Initial answer:* Local sentence-transformers for privacy consistency

2. **Content extraction quality:** How to handle paywalled articles?
   - *Initial answer:* Mark as "failed - paywall" and skip; don't try to bypass

3. **Project name:** Need a catchy name for the repo
   - Ideas: `bookmark-brain`, `recall`, `stash-search`, `bookmark-oracle`

4. **Streamlit vs custom UI:** Streamlit is faster to build but less polished
   - *Initial answer:* Start with Streamlit, migrate if it becomes popular

---

## 10. Timeline & Milestones

### 1-Week Sprint (assuming ~10-15 hours)

**Days 1-2: Core Infrastructure**
- Chrome bookmark import parsing
- SQLite schema and storage
- Basic content fetching with readability

**Days 3-4: Search + RAG**
- Embedding generation with sentence-transformers
- Vector storage with ChromaDB
- Hybrid search implementation
- LLM integration with citation formatting

**Days 5-6: UI + Polish**
- Streamlit interface (chat, library, settings)
- Error handling and edge cases
- README and setup documentation

**Day 7: Launch**
- Final testing
- GitHub repo setup with LICENSE, README
- LinkedIn post draft

---

## 11. Appendix

### Example Query Flow:

**User asks:** "I'm thinking of negotiating my salary by sharing competing offers. Any advice from my bookmarks?"

**System:**
1. Embeds query using sentence-transformers
2. Searches vector DB for similar content chunks
3. Also runs keyword search for "salary," "negotiation," "competing offers"
4. Retrieves top 15 relevant chunks from ~8 different bookmarks
5. Sends to LLM with prompt: "Based on these sources, answer the user's question. Cite sources using [1], [2], etc."
6. Returns synthesized answer with citations:

> "Several of your saved articles discuss this. [1] suggests sharing competing offers can be effective but recommends framing it as 'I want to make this work' rather than an ultimatum. However, [2] warns this can backfire if the company feels you're not committed. [3] recommends having a specific number in mind rather than just showing offers..."
>
> **Sources:**  
> [1] How to Negotiate Salary - hbr.org  
> [2] 10 Salary Negotiation Mistakes - themuse.com  
> [3] Negotiation Tactics That Work - forbes.com

---

**Status:** Ready for task breakdown  
**Next Step:** Generate task list using tasks template
