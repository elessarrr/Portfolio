# Product Requirements Document: Aircraft Safety History Lookup Tool

**ROOT DIRECTORY:** All work for this project should be performed within the `Aircraft Safety Tracker` directory.

**Project ID:** 0001  
**Created:** December 2025  
**Target Launch:** January 2026 (2-week sprint)  
**Author:** Raj  

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

### Why This Stack?

**Flask over FastAPI:**
- Simpler for MVP (less boilerplate, mature ecosystem)
- Better template integration with Jinja2
- Perfect for server-side rendering
- Excellent documentation for beginners

**Server-Side Rendering over React/Next.js:**
- ✅ Single language (Python only)
- ✅ No JavaScript build tools needed
- ✅ Faster development for read-heavy apps
- ✅ Better initial page load performance
- ✅ SEO-friendly by default

**HTMX for Interactivity:**
- Adds modern features (autocomplete, live filters) without JavaScript frameworks
- Works seamlessly with Jinja2 templates
- Minimal learning curve
- Progressive enhancement (degrades gracefully without JS)

**SQLite over PostgreSQL:**
- Zero configuration (no separate database server)
- Perfect for read-heavy workloads (~40 aircraft models)
- Easy backups (single .db file)
- Railway supports SQLite via persistent volumes

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
- fatalities
- description
- asn_link
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

### Data Collection Strategy
**Phase 1 (Week 1):**
- Manually collect data for all Boeing commercial aircraft (15-20 models)
- Manually collect data for all Airbus commercial aircraft (15-20 models)
- Source: Aviation Safety Network database
- Format: JSON files → import to SQLite

**Data Structure Per Aircraft:**
- Visit ASN search page for each model
- Extract: incident count, list of incidents with details
- Store notable incidents (fatal or significant non-fatal)
- Generate AI summary using collected data

**Coverage Goal:** 30-40 aircraft models covering 90%+ of commercial flights

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

7. **Career Impact:**
   - Project mentioned in job interviews
   - Used as portfolio case study in applications
   - Generates speaking opportunities beyond initial conference

### Measurement Tools
- **Analytics:** Plausible.io or Simple Analytics (privacy-focused)
- **Search Tracking:** Custom event logging (model searched, timestamp)
- **User Requests:** Form submissions tracked in backend
- **LinkedIn:** Native LinkedIn analytics on launch post

---

## 9. Open Questions

### Data Questions:
1. **How frequently should we update the database with new ASN incidents?**
   - Initial answer: Manual updates monthly, automate if traction warrants
   
2. **Should we include incidents from aircraft still in testing/not in commercial service?**
   - Initial answer: No, focus on commercial passenger aircraft only

3. **What's the threshold for "notable incident" to include in detailed list?**
   - Initial answer: All fatal incidents + non-fatal with hull loss or injuries

### Product Questions:
4. **Should we show "aircraft with zero incidents" as a positive signal?**
   - Initial answer: Yes, with caveat "based on publicly reported data"

5. **How do we handle regional variants (e.g., 737-800 vs 737-800W)?**
   - Initial answer: Group together unless significantly different safety record

6. **Should flight number search be in MVP or deferred?**
   - Initial answer: Defer to post-MVP, requires additional APIs and complexity

### Business/Strategy Questions:
7. **Should we reach out to ASN for formal data partnership?**
   - Initial answer: Start by crediting/linking them, reach out if tool gains traction

8. **Is there a path to B2B API licensing (Skyscanner, Google Flights)?**
   - Initial answer: Build proof-of-concept first, pitch later if validated

9. **Should we monetize with ads or keep completely free?**
   - Initial answer: Keep free for MVP, portfolio value > revenue at this stage

### Technical Questions:
10. **Which LLM API is most cost-effective for summaries?**
    - Decision: Google Gemini API (free tier: 1M tokens/month, 15 req/min - more than sufficient for MVP)

11. **Should we pre-generate all AI summaries or generate on-demand?**
    - Initial answer: Pre-generate during data collection, cache aggressively

12. **How do we handle ASN data copyright/terms of use?**
    - Initial answer: Review ASN terms, we're linking to them and crediting source (fair use)

---

## 10. Timeline & Milestones

### 2-Week Sprint Plan

**Week 1: Data + Backend**
- **Day 1-2:** Data collection (Boeing models from ASN)
- **Day 3-4:** Data collection (Airbus models from ASN)
- **Day 5:** Backend API setup (Flask/FastAPI + SQLite)
- **Day 6:** AI summary generation + caching
- **Day 7:** Backend testing, API endpoint validation

**Week 2: Frontend + Launch**
- **Day 8-9:** Frontend UI development (search, results display)
- **Day 10:** Chart/visualization integration
- **Day 11:** Mobile responsive testing + bug fixes
- **Day 12:** Deploy to production (Vercel + Railway)
- **Day 13:** Content creation (blog post, demo video, screenshots)
- **Day 14:** Launch on LinkedIn, Reddit, Product Hunt

### Post-Launch (Week 3+)
- Monitor analytics, fix bugs
- Respond to user feedback
- Add requested aircraft models
- Iterate on UX based on real usage

---

## 11. Dependencies & Risks

### Dependencies:
1. **Aviation Safety Network data accessibility** - Confirmed: publicly available
2. **LLM API access** - Google Gemini API (free tier account)
3. **Deployment platform availability** - Vercel/Railway free tiers sufficient
4. **2-week sprint window** - User has dedicated leave time

### Risks & Mitigation:

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| ASN data more complex than expected | High | Medium | Allocate extra day for data cleaning |
| AI summaries generate inaccurate info | High | Medium | Human review all summaries before launch |
| Legal concerns about liability | Medium | Low | Prominent disclaimers, link to source data |
| Low initial traffic | Low | Medium | Launch across multiple channels, leverage Boeing news cycle |
| Data becomes outdated quickly | Medium | Low | Monthly update process, display last-updated date |
| User requests for unsupported aircraft | Low | High | Clear messaging + request form to capture demand |

---

## 12. Appendix

### Target Aircraft Models (Initial Coverage)

**Boeing Commercial Aircraft (~20 models):**
- 737 Family: -700, -800, -900, -900ER, MAX 7, MAX 8, MAX 9, MAX 10
- 747 Family: -400, -8 (if still in passenger service)
- 757 Family: -200, -300
- 767 Family: -300, -400
- 777 Family: -200, -200ER, -300, -300ER
- 787 Family: -8, -9, -10

**Airbus Commercial Aircraft (~20 models):**
- A220 Family: -100, -300
- A319: A319, A319neo
- A320 Family: A320-200, A320neo
- A321 Family: A321-200, A321neo, A321XLR
- A330 Family: -200, -300, -800neo, -900neo
- A350 Family: -900, -1000
- A380: -800

**Total Coverage:** ~40 aircraft models representing 90%+ of commercial passenger flights worldwide

### Reference Links
- Aviation Safety Network: https://aviation-safety.net/database/
- NTSB Database: https://www.ntsb.gov/Pages/AviationQuery.aspx
- Planespotters (fleet data): https://www.planespotters.net/
- FlightAware (for potential future flight lookup): https://flightaware.com/

### Competitive Analysis
**Existing Tools (Gaps we fill):**
- **AirlineRatings.com:** Rates airlines, not specific aircraft models
- **Aviation Safety Network:** Comprehensive but not user-friendly for average travelers
- **SeatGuru:** Focuses on seat maps, not safety history
- **Skyscanner/Google Flights:** No safety information at all

**Our Differentiator:** Only tool focused on aircraft MODEL safety history with user-friendly interface and AI contextual summaries.

---

## Approval & Sign-off

**Created by:** Raj  
**Date:** December 2025  
**Status:** Ready for Development  
**Next Step:** Generate task breakdown using tasks template

---

*This PRD is a living document and will be updated based on user feedback and technical discoveries during implementation.*