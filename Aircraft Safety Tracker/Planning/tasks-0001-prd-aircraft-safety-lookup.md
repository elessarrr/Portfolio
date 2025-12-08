# Task List: Aircraft Safety History Lookup Tool

**ROOT DIRECTORY:** All work for this project should be performed within the `Aircraft Safety Tracker` directory.

**PRD Reference:** 0001-prd-aircraft-safety-lookup.md  
**Target:** 2-week MVP sprint  
**Created:** December 2025

---

## Relevant Files

### Application Structure (Flask Monolith)
- `app/__init__.py` - Flask app initialization, configuration, extensions
- `app/routes.py` - All routes (pages + HTMX endpoints)
- `app/models.py` - SQLAlchemy database models (Aircraft, Incident, Request)
- `app/forms.py` - Flask-WTF forms for user input validation
- `app/services/gemini.py` - Google Gemini API wrapper for AI summaries
- `app/services/search.py` - Search logic and autocomplete
- `config.py` - Configuration classes (Dev, Production)
- `run.py` - Application entry point

### Templates (Jinja2)
- `app/templates/base.html` - Base layout with navbar, footer, disclaimers
- `app/templates/index.html` - Home page with search bar
- `app/templates/aircraft.html` - Aircraft detail page
- `app/templates/about.html` - About page with data sources
- `app/templates/components/search_results.html` - Autocomplete dropdown (HTMX fragment)
- `app/templates/components/incident_list.html` - Filterable incident table (HTMX fragment)
- `app/templates/components/stats_card.html` - Statistics display card
- `app/templates/components/summary_card.html` - AI summary display

### Static Assets
- `app/static/css/styles.css` - Custom CSS (minimal, mostly Tailwind)
- `app/static/js/main.js` - HTMX configuration and custom interactions

### Data & Scripts
- `scripts/scrape_boeing.py` - Scrape Boeing aircraft from ASN
- `scripts/scrape_airbus.py` - Scrape Airbus aircraft from ASN
- `scripts/import_data.py` - Load scraped JSON into SQLite database
- `scripts/generate_summaries.py` - Pre-generate AI summaries using Gemini
- `data/raw/boeing_incidents.json` - Raw scraped Boeing data
- `data/raw/airbus_incidents.json` - Raw scraped Airbus data
- `data/aircraft_safety.db` - SQLite database (created by SQLAlchemy)

### Testing
- `tests/conftest.py` - Pytest fixtures and test configuration
- `tests/test_routes.py` - Test all Flask routes
- `tests/test_models.py` - Test database models
- `tests/test_search.py` - Test search functionality
- `tests/test_gemini.py` - Test AI summary generation (with mocks)

### Configuration
- `requirements.txt` - Python dependencies
- `.env.example` - Example environment variables
- `.gitignore` - Git ignore rules
- `Procfile` - Railway deployment configuration
- `README.md` - Project documentation and setup instructions

### Notes

- **Testing:** Run `pytest` from project root to execute all tests
- **Development Server:** Run `python run.py` to start Flask dev server
- **Database Migrations:** Using `flask db` commands (Flask-Migrate)
- **HTMX:** Included via CDN in `base.html` (no npm needed)
- **Tailwind CSS:** Included via CDN (no build process)

---

## Tasks

- [x] 1.0 Project Setup & Infrastructure
  - [x] 1.1 Initialize Git repository with proper `.gitignore` (Python, SQLite, `.env`)
  - [x] 1.2 Create project directory structure (`app/`, `scripts/`, `data/`, `tests/`)
  - [x] 1.3 Create `requirements.txt` with dependencies: Flask, SQLAlchemy, Flask-WTF, Flask-Migrate, Flask-Caching, pytest, pytest-flask, httpx, beautifulsoup4, google-generativeai
  - [x] 1.4 Set up Python virtual environment and install dependencies (`python -m venv venv && source venv/bin/activate && pip install -r requirements.txt`)
  - [x] 1.5 Create `config.py` with configuration classes (Development, Production) including SECRET_KEY, DATABASE_URI, GEMINI_API_KEY
  - [x] 1.6 Create `.env.example` with required environment variables template
  - [x] 1.7 Create Flask app initialization in `app/__init__.py` (register extensions, blueprints)
  - [x] 1.8 Create `run.py` as application entry point
  - [x] 1.9 Test that Flask app runs successfully on localhost:5000

- [ ] 2.0 Database Design & Models
  - [x] 2.1 Design database schema in `app/models.py`: Aircraft table (id, manufacturer, model_name, icao_code, years_in_service, total_incidents, fatal_incidents, total_fatalities, ai_summary, last_updated)
  - [ ] 2.2 Add Incident table to `app/models.py` (id, aircraft_id FK, date, operator, location, fatalities, description, asn_url, incident_type)
  - [ ] 2.3 Add Request table to `app/models.py` for user feedback (id, aircraft_model, user_email nullable, created_at)
  - [ ] 2.4 Initialize Flask-Migrate and create initial migration (`flask db init && flask db migrate -m "Initial schema"`)
  - [ ] 2.5 Apply migration to create SQLite database (`flask db upgrade`)
  - [ ] 2.6 Write pytest tests in `tests/test_models.py` to verify model creation and relationships
  - [ ] 2.7 Run tests to confirm database models work correctly

- [ ] 3.0 Data Collection & Import
  - [ ] 3.1 Write ASN scraper in `scripts/scrape_boeing.py` using BeautifulSoup and httpx (scrape Boeing 737 family, 747, 757, 767, 777, 787)
  - [ ] 3.2 Run Boeing scraper and save output to `data/raw/boeing_incidents.json`
  - [ ] 3.3 Manually review Boeing data for quality (check ~5 sample aircraft)
  - [ ] 3.4 Write ASN scraper in `scripts/scrape_airbus.py` (scrape A220, A319, A320, A321, A330, A350, A380)
  - [ ] 3.5 Run Airbus scraper and save output to `data/raw/airbus_incidents.json`
  - [ ] 3.6 Manually review Airbus data for quality
  - [ ] 3.7 Write data import script in `scripts/import_data.py` to load JSON into SQLite via SQLAlchemy
  - [ ] 3.8 Run import script and verify ~40 aircraft models loaded with incidents
  - [ ] 3.9 Write SQL query to validate data integrity (check for nulls, count incidents per aircraft)

- [ ] 4.0 Backend Routes & Logic
  - [ ] 4.1 Create base template in `app/templates/base.html` with Tailwind CDN, HTMX CDN, navbar, footer, disclaimer banner
  - [ ] 4.2 Implement home page route `GET /` and template `app/templates/index.html` with centered search bar
  - [ ] 4.3 Implement search autocomplete endpoint `GET /search?q=<query>` that returns HTML `<li>` elements
  - [ ] 4.4 Create autocomplete template fragment `app/templates/components/search_results.html`
  - [ ] 4.5 Implement aircraft detail route `GET /aircraft/<model_name>` in `app/routes.py`
  - [ ] 4.6 Create aircraft detail template `app/templates/aircraft.html` with stats card, incident list, AI summary
  - [ ] 4.7 Implement incident filtering endpoint `GET /aircraft/<model>/incidents?filter=<fatal|nonfatal>&date_from=&date_to=` (returns HTML fragment)
  - [ ] 4.8 Create incident list template `app/templates/components/incident_list.html` (table with sorting)
  - [ ] 4.9 Implement feedback submission route `POST /feedback/request` using Flask-WTF form
  - [ ] 4.10 Add error handling for 404 (aircraft not found) with suggested similar models
  - [ ] 4.11 Write tests in `tests/test_routes.py` for all routes (status codes, content checks)

- [ ] 5.0 AI Integration & Summary Generation
  - [ ] 5.1 Create Google Gemini API client in `app/services/gemini.py` with rate limiting and error handling
  - [ ] 5.2 Design prompt template for aircraft summaries (context: overall record, notable incidents, groundings, current operational status)
  - [ ] 5.3 Implement summary generation function that accepts aircraft data dict and returns 3-5 sentence summary
  - [ ] 5.4 Add summary caching: store generated summaries in Aircraft.ai_summary column
  - [ ] 5.5 Create script `scripts/generate_summaries.py` to batch-generate summaries for all aircraft
  - [ ] 5.6 Run summary generation script for all ~40 aircraft (takes ~3 minutes with rate limiting)
  - [ ] 5.7 Manually review 5 sample summaries for accuracy and tone
  - [ ] 5.8 Create summary display template `app/templates/components/summary_card.html` with disclaimer
  - [ ] 5.9 Add endpoint to regenerate summary if needed `GET /aircraft/<model>/regenerate-summary` (admin only or manual trigger)
  - [ ] 5.10 Write tests in `tests/test_gemini.py` using mock responses

- [ ] 6.0 Frontend Interactivity & Styling
  - [ ] 6.1 Configure HTMX in `app/static/js/main.js` (set default swap strategy, error handling)
  - [ ] 6.2 Implement autocomplete with HTMX: search input triggers `hx-get="/search"` on keyup
  - [ ] 6.3 Style autocomplete dropdown with Tailwind classes (position absolute, z-index, hover states)
  - [ ] 6.4 Implement incident filtering with HTMX: filter buttons trigger `hx-get="/aircraft/<model>/incidents?filter=..."`
  - [ ] 6.5 Add loading indicators for HTMX requests (use `htmx:beforeRequest` and `htmx:afterRequest` events)
  - [ ] 6.6 Style all components with Tailwind following PRD color palette (deep blue #1e3a8a, amber #f59e0b)
  - [ ] 6.7 Implement mobile-responsive navigation (hamburger menu, stack layout)
  - [ ] 6.8 Test mobile responsiveness on 375px (iPhone SE), 768px (iPad), 1024px (desktop) viewports
  - [ ] 6.9 Add custom CSS in `app/static/css/styles.css` for any styles not covered by Tailwind
  - [ ] 6.10 Ensure all interactive elements have hover/focus states and are keyboard-accessible

- [ ] 7.0 Testing, Deployment & Launch
  - [ ] 7.1 Run full test suite (`pytest -v`) and ensure all tests pass
  - [ ] 7.2 Manual testing: search for 10 different aircraft models across manufacturers
  - [ ] 7.3 Manual testing: verify all filters work (fatal/non-fatal, date ranges)
  - [ ] 7.4 Manual testing: test on real mobile devices (iOS Safari, Android Chrome)
  - [ ] 7.5 Manual testing: verify autocomplete works smoothly (no lag, handles typos)
  - [ ] 7.6 Create Railway account and initialize new project
  - [ ] 7.7 Configure Railway environment variables (SECRET_KEY, GOOGLE_GEMINI_API_KEY, FLASK_ENV=production)
  - [ ] 7.8 Create `Procfile` for Railway: `web: gunicorn run:app`
  - [ ] 7.9 Add `gunicorn` to `requirements.txt`
  - [ ] 7.10 Deploy to Railway via GitHub integration (connect repo, auto-deploy on push)
  - [ ] 7.11 Upload SQLite database with pre-generated summaries to Railway persistent volume
  - [ ] 7.12 Test production deployment: verify all routes work, database accessible, AI summaries display
  - [ ] 7.13 Set up Plausible Analytics (add script tag to `base.html`)
  - [ ] 7.14 Create launch content: LinkedIn post draft emphasizing portfolio value
  - [ ] 7.15 Create demo GIF or video showing search → results flow
  - [ ] 7.16 Take screenshots for portfolio (home page, sample aircraft detail page)
  - [ ] 7.17 Launch on LinkedIn and relevant communities
  - [ ] 7.18 Monitor analytics and error logs for first 24 hours, fix critical issues immediately

---

## Implementation Notes for Junior Developers

### Development Workflow
1. **Work on ONE sub-task at a time**
2. After completing a sub-task, mark it `[x]`
3. When ALL sub-tasks under a parent are complete:
   - Run tests: `pytest`
   - If tests pass: `git add . && git commit -m "descriptive message"`
   - Mark parent task `[x]`
4. Request permission before starting next sub-task

### Essential Commands

**Setup:**
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Initialize database
flask db init
flask db migrate -m "Initial schema"
flask db upgrade
```

**Development:**
```bash
# Run Flask dev server
python run.py

# Run tests
pytest                    # All tests
pytest tests/test_routes.py  # Specific file
pytest -v                 # Verbose output
pytest -k "test_search"   # Run tests matching pattern
```

**Database:**
```bash
# Create new migration after model changes
flask db migrate -m "Add new field"

# Apply migrations
flask db upgrade

# Rollback migration
flask db downgrade
```

### Tech Stack Summary
- **Framework:** Flask 3.0+ (Python web framework)
- **Templates:** Jinja2 (server-side HTML)
- **Interactivity:** HTMX 1.9+ (dynamic updates)
- **Database:** SQLite + SQLAlchemy ORM
- **Styling:** Tailwind CSS (via CDN)
- **AI:** Google Gemini 1.5 Flash (free tier)
- **Testing:** pytest + pytest-flask
- **Deployment:** Railway.app (free tier)

### HTMX Basics (You'll Need This!)

HTMX lets you add interactivity without writing JavaScript:

```html
<!-- Autocomplete example -->
<input 
  type="text" 
  name="search"
  hx-get="/search"
  hx-trigger="keyup changed delay:300ms"
  hx-target="#results"
  hx-swap="innerHTML"
>
<div id="results"></div>
```

**What this does:**
1. User types → waits 300ms → sends GET request to `/search`
2. Server returns HTML fragment
3. HTMX swaps it into `#results` div
4. No page reload!

### Key PRD Requirements
- **Mobile-first:** Test on small screens constantly
- **Prominent disclaimers:** Data is informational only
- **Clear sourcing:** Always link to ASN for verification
- **No user accounts:** Keep it simple
- **Focus on MVP:** Defer nice-to-have features if time is tight

### Useful Resources
- Flask docs: https://flask.palletsprojects.com/
- HTMX docs: https://htmx.org/docs/
- SQLAlchemy docs: https://docs.sqlalchemy.org/
- Tailwind docs: https://tailwindcss.com/docs
- Google Gemini API: https://ai.google.dev/
- Aviation Safety Network: https://aviation-safety.net/database/

### Common Gotchas
1. **HTMX fragments must be valid HTML** - even if they're just `<li>` items
2. **SQLAlchemy sessions** - always commit after changes: `db.session.commit()`
3. **Flask context** - some operations need `with app.app_context():`
4. **Rate limiting** - Gemini free tier: 15 requests/min
5. **Railway volumes** - SQLite needs persistent volume, not ephemeral storage
