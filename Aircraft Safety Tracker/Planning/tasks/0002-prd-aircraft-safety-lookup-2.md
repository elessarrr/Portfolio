# Product Requirements Document: Aircraft Safety History Lookup Tool (v2)

**ROOT DIRECTORY:** All work for this project should be performed within the `Aircraft Safety Tracker` directory.

**Project ID:** 0002  
**Created:** December 2025  
**Target Launch:** January 2026 (2-week sprint)  
**Author:** Raj  
**Previous Version:** 0001-prd-aircraft-safety-lookup.md

---

## 1. Introduction/Overview

### Problem Statement
Travelers have no easy way to check the safety history of aircraft models before booking flights, despite comprehensive public safety data being available but scattered across difficult-to-navigate databases. This information asymmetry prevents informed decision-making at the point of booking.

### Solution
A web-based tool that aggregates aircraft incident data from the Aviation Safety Network (ASN) and presents it in an accessible, user-friendly format. Users can search by aircraft model to instantly see historical safety records, incident summaries, and AI-generated contextual analysis.

### Goal
Enable travelers to make more informed flight choices by providing transparent access to aircraft safety history data, reducing decision fatigue when choosing between competing flights on the same route.

---

## 2. Goals

### Primary Goals
1. **Transparency:** Make publicly available aircraft safety data accessible to average travelers
2. **Decision Support:** Help users filter flight options based on aircraft model safety history
3. **Portfolio Demonstration:** Showcase data aggregation, API integration, and product thinking skills in the Transportation/Mobility sector
4. **LinkedIn Engagement:** Generate 500+ searches in first month, demonstrating product-market fit

### Secondary Goals
1. Demonstrate LLM integration for contextual summaries
2. Explore potential B2B applications (API for travel booking platforms)
3. Expand into 4th vertical for portfolio diversification (already have: Sustainability, Energy, Manufacturing)

---

## 3. User Stories

### Primary User: Nervous Flyer
**As a nervous flyer,**  
I want to check if my booked aircraft model has a concerning incident history,  
So that I can make an informed decision about whether to keep my booking or choose an alternative flight.

### Primary User: Safety-Conscious Traveler
**As a safety-conscious traveler,**  
I want to compare the safety records of different aircraft types on competing flights,  
So that I can choose the option I'm most comfortable with.

### Primary User: Route Comparison Shopper
**As a traveler choosing between multiple flights on the same route,**  
I want to know if a particular aircraft model is marginally safer than alternatives,  
So that I can use this as an additional filter to reduce decision fatigue when all other factors (price, timing) are similar.

### Secondary User: Aviation Enthusiast
**As an aviation enthusiast,**  
I want to explore incident histories across different aircraft models,  
So that I can understand aviation safety trends and aircraft evolution.

---

## 4. Functional Requirements

### FR-1: Aircraft Model Search (MUST HAVE)
**The system must allow users to search for aircraft models by name or designation.**

- **FR-1.1:** Search input accepts common formats:
  - Manufacturer + model: "Boeing 737-800", "Airbus A320"
  - Informal: "737 MAX", "A380"
  - ICAO codes: "B738", "A320"
- **FR-1.2:** Search provides autocomplete suggestions from database
- **FR-1.3:** Search is case-insensitive and handles common variations
- **FR-1.4:** Invalid searches show helpful error message: "Aircraft model not found. Try: [suggest 3 similar models]"

### FR-2: Incident History Display (MUST HAVE)
**The system must display comprehensive incident data for searched aircraft models.**

- **FR-2.1:** Display summary statistics:
  - Total incidents in ASN database
  - Fatal incidents count
  - Total fatalities across all incidents
  - Years of service
- **FR-2.2:** Display list of notable incidents including:
  - Date
  - Operator (airline)
  - Location
  - Fatalities (if any)
  - Brief description (1-2 sentences)
  - Link to full ASN report
- **FR-2.3:** Incidents sorted by date (most recent first)
- **FR-2.4:** Option to filter by: fatal/non-fatal, date range, operator

### FR-3: AI-Generated Summary (MUST HAVE)
**The system must provide contextual AI-generated summaries of safety history.**

- **FR-3.1:** Generate 3-5 sentence summary covering:
  - Overall safety track record context
  - Notable incidents or patterns
  - Any groundings or major regulatory actions
  - Current operational status
- **FR-3.2:** Summary updates when new incidents are added to database
- **FR-3.3:** Cite data sources clearly (ASN, NTSB)
- **FR-3.4:** Include disclaimer: "AI-generated summary for informational purposes only"

### FR-4: Timeline Visualization (NICE TO HAVE)
**The system should provide visual timeline of incidents.**

- **FR-4.1:** Interactive chart showing incidents over time
- **FR-4.2:** Distinguish fatal vs. non-fatal incidents visually
- **FR-4.3:** Hoverable tooltips show incident details
- **FR-4.4:** Zoom/pan functionality for dense timelines

### FR-5: Model Comparison (NICE TO HAVE)
**The system should allow side-by-side comparison of aircraft models.**

- **FR-5.1:** Users can select 2-3 aircraft models to compare
- **FR-5.2:** Display comparative statistics in table format
- **FR-5.3:** Highlight significant differences
- **FR-5.4:** Include AI-generated comparative summary

### FR-6: User Feedback Mechanism (MUST HAVE)
**The system must allow users to request aircraft models not in database.**

- **FR-6.1:** "Request Aircraft" button on "not found" pages
- **FR-6.2:** Simple form: aircraft model name, email (optional)
- **FR-6.3:** Submissions stored for prioritization
- **FR-6.4:** Confirmation message: "Thanks! We'll prioritize adding [aircraft]"

### FR-7: Data Transparency (MUST HAVE)
**The system must clearly communicate data sources and limitations.**

- **FR-7.1:** Prominent disclaimer on every page:
  - "Data sourced from Aviation Safety Network"
  - "Includes reported accidents and serious incidents"
  - "Does not include minor maintenance issues"
  - "For informational purposes only, not safety advice"
  - "Incident history does not predict future safety"
- **FR-7.2:** Display last database update date
- **FR-7.3:** Link to ASN database for verification
- **FR-7.4:** Note aircraft models currently tracked (count)

### FR-8: Mobile Responsiveness (MUST HAVE)
**The system must be fully functional on mobile devices.**

- **FR-8.1:** Responsive design adapts to screen sizes
- **FR-8.2:** Touch-friendly interface elements
- **FR-8.3:** Optimized load times for mobile data
- **FR-8.4:** Search and core features accessible without horizontal scrolling

---

## 5. Non-Goals (Out of Scope)

### Explicitly NOT Building:
1. **Airline Safety Ratings** - Focus is aircraft models, not airline operational safety
2. **Future Safety Predictions** - Only historical data, no predictive analytics
3. **Booking Integration** - Not directly integrated with booking platforms (MVP)
4. **Real-time Flight Tracking** - Not tracking specific flights in real-time
5. **Flight Recommendation Engine** - No "book this flight" suggestions
6. **User Accounts/Profiles** - No login required for MVP
7. **Email Notifications** - No alerts for new incidents (future feature)
8. **Comprehensive Database** - Starting with Boeing/Airbus only, not every aircraft ever built
9. **Maintenance Records** - Only publicly reported incidents, not routine maintenance
10. **Insurance/Legal Advice** - Strictly informational, no liability assumptions

---

## 6. Design Considerations

### Design Philosophy
**Clean, minimal, data-forward design** prioritizing usability and information clarity over visual complexity.

### Key Design Principles:
1. **Google-like Simplicity:** Prominent search bar, minimal chrome
2. **Data Hierarchy:** Most important info (summary stats) above the fold
3. **Scanability:** Use whitespace, clear typography, logical grouping
4. **Trust Signals:** Professional appearance, clear sourcing, prominent disclaimers
5. **Mobile-First:** Design for mobile experience, enhance for desktop

### Visual Style:
- **Color Palette:** 
  - Primary: Deep blue (#1e3a8a) - trust, aviation
  - Accent: Amber (#f59e0b) - caution/attention
  - Neutral: Grays for text and backgrounds
  - Success: Green for "no incidents"
  - Danger: Red for fatal incidents (use sparingly)
- **Typography:** 
  - Headers: Clean sans-serif (Inter, Roboto, or system fonts)
  - Body: Readable at 16px minimum
  - Monospace for aircraft codes (e.g., "B738")
- **Icons:** Minimal use, only for clarity (search, filter, external link)

### UI Components:
1. **Search Bar:** Centered, prominent, with autocomplete dropdown
2. **Summary Card:** Key statistics in easy-to-scan format
3. **Incident List:** Collapsed by default, expandable for details
4. **AI Summary Box:** Visually distinct, clearly labeled as AI-generated
5. **Chart/Timeline:** Interactive, responsive, optional based on data volume
6. **Footer:** Data source, disclaimers, feedback link

### Responsive Breakpoints:
- Mobile: < 640px (single column, stacked cards)
- Tablet: 640-1024px (optimize spacing)
- Desktop: > 1024px (max-width container, optimal line length)

---

## 7. Technical Considerations

### Technology Stack (Simplified Python-Only)

**Single Application (Flask):**
- **Backend Framework:** Flask 3.0+ (Python)
- **Templates:** Jinja2 (server-side HTML rendering)
- **Interactivity:** HTMX 1.9+ (dynamic updates without page reloads)
- **Database:** SQLite + SQLAlchemy ORM
- **Styling:** Tailwind CSS (via CDN, no build tools)
- **AI:** Google Gemini 1.5 Flash API (free tier)

**Development & Testing:**
- **Testing:** pytest + pytest-flask
- **Data Collection:** BeautifulSoup4 + httpx
- **Deployment:** Railway.app (single app, free tier)
- **Version Control:** Git + GitHub

### Architecture Overview

**Single Monolithic Application:**
```
Flask App
├── Routes (handle requests)
├── Jinja2 Templates (render HTML)
├── HTMX (client-side interactivity)
├── SQLAlchemy (database queries)
└── Services (Gemini API, search logic)
```

**Request Flow:**
```
User types in search bar
  → HTMX sends request to Flask
  → Flask queries SQLite via SQLAlchemy
  → Jinja2 renders HTML fragment
  → HTMX swaps fragment into page (no reload)
```

### Data Architecture

**Database Schema:**
```
Aircraft Model:
- model_id (primary key)
- manufacturer (Boeing, Airbus)
- model_name (737-800, A320-200)
- variant (optional)
- icao_code (B738, A320)
- years_in_service
- total_incidents
- fatal_incidents
- total_fatalities
- ai_summary (cached)
- last_updated

Incident:
- incident_id (primary key)
- model_id (foreign key)
- date
- operator
- location
- fatalities (scraped from details page)
- description (scraped from "Narrative" section)
- asn_link (scraped from date column hyperlink)
- incident_type (fatal/non-fatal)
```

### Routes (Flask Pages & HTMX Endpoints)

**Page Routes:**
```
GET /
- Home page with search bar

GET /aircraft/<model_name>
- Aircraft detail page with incidents and AI summary

GET /about
- About page with data sources and disclaimers
```

**HTMX Endpoints (return HTML fragments):**
```
GET /search?q=<query>
- Returns autocomplete suggestions as <li> elements

GET /aircraft/<model_name>/incidents?filter=<fatal|nonfatal>&date_from=<date>&date_to=<date>
- Returns filtered incident list HTML

POST /feedback/request
- Submit aircraft model request (shows success message)
```

### Data Collection Strategy (v2)
**Phase 1 (Week 1):**
- **Source:** Aviation Safety Network "Accidents by aeroplane type" index (e.g., `https://aviation-safety.net/database/type/`).
- **Method:**
  1.  **Index Scrape:** Visit the main type index page.
  2.  **Filter:** Identify links for target manufacturers (Boeing, Airbus) and models (e.g., "Boeing 737", "Airbus A320").
  3.  **Model Scrape:** For each model URL, scrape the table of incidents.
      - Columns: Date, Type, Registration, Operator, Fatalities, Location, Category.
  4.  **Deep Dive:** **CRITICAL STEP.** For every incident in the table, **follow the "Date" hyperlink** to the incident details page.
  5.  **Detail Scrape:** From the details page, extract:
      - **Narrative:** The full textual description of the event.
      - **Fatalities:** Precise count (confirming the summary table).
      - **Classification:** (e.g., Accident, Incident, Hijacking).
  6.  **Storage:** Save as JSON first, then import to SQLite.

**Coverage Goal:** 30-40 aircraft models covering 90%+ of commercial flights.
- **Boeing:** 737 (all gens), 747, 757, 767, 777, 787.
- **Airbus:** A220, A300, A310, A318/319/320/321 (CEO & NEO), A330, A340, A350, A380.

### Performance Considerations
- **Database queries:** < 100ms (SQLite is fast for small datasets)
- **Page load:** < 2 seconds on 3G (server-rendered HTML = fast first paint)
- **HTMX updates:** < 500ms (partial HTML swaps feel instant)
- **AI summaries:** Pre-cached in database (no generation delay)
- **Caching:** Flask-Caching for frequent queries (aircraft list, search results)
- **Images:** Minimal/none for fast loading

### Security/Privacy
- **No user data collection:** No login, no tracking beyond basic analytics
- **Rate limiting:** Flask-Limiter on search endpoints (prevent scraping abuse)
- **Input sanitization:** SQLAlchemy ORM prevents SQL injection
- **CSRF protection:** Flask-WTF for form submissions
- **HTTPS only:** Railway provides free SSL certificates

---

## 8. Success Metrics

### Primary Metrics (MVP - First Month)
1. **Usage Metrics:**
   - **Target:** 500+ total searches performed
   - **Target:** 200+ unique visitors
   - **Target:** 30+ distinct aircraft models searched

2. **Engagement Metrics:**
   - **Target:** Average 2+ minutes time on site
   - **Target:** 30%+ users search for multiple models
   - **Target:** 10+ aircraft model requests submitted

3. **LinkedIn/Portfolio Metrics:**
   - **Target:** Launch post generates 100+ reactions
   - **Target:** 20+ meaningful comments/discussions
   - **Target:** 3+ recruiters/companies reach out
   - **Target:** Featured in portfolio during conference networking

### Secondary Metrics (Quality Indicators)
4. **User Satisfaction:**
   - Qualitative feedback: positive sentiment in comments
   - Low bounce rate (<50% on results pages)
   - Repeat visitors (10%+ returning users)

5. **Technical Performance:**
   - Zero critical bugs in first week
   - API uptime >99%
   - Page load time <2 seconds maintained

### Long-term Success Indicators (3-6 months)
6. **Growth Trajectory:**
   - 2,000+ searches per month
   - Organic traffic growth month-over-month
   - Media mentions or blog features
