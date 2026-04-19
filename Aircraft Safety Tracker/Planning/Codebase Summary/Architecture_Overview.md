# Architecture Overview: Aircraft Safety Tracker

### 1. Application Overview

The Aircraft Safety Tracker is a web application that aggregates, normalizes, and analyzes aviation safety incidents across multiple data sources (NTSB, FAA, ASN). It provides an interface for users to search aircraft models, view historical safety timelines, and leverage Large Language Models (LLMs) to generate concise safety summaries and extract structured findings from official accident reports.

### 2. Tech Stack

- **Languages:** Python, JavaScript, HTML, CSS
- **Web Frameworks:** Flask (Backend), HTMX (Frontend interactivity)
- **Data Layer:** SQLAlchemy ORM, Alembic (Migrations)
- **Databases:** SQLite (Development) / PostgreSQL (Production), Redis (Message Broker)
- **External APIs:** NTSB CAROL API, FAA DRS APIs, DeepSeek API, Google Gemini API
- **Testing/Tooling:** Pytest, Ruff, Mypy

### 3. High-Level Component Breakdown

- **Frontend UI:** Server-rendered Jinja2 templates enhanced with HTMX for dynamic, partial page updates (e.g., polling for background job completion, filtering incident lists) without writing heavy client-side JavaScript.
- **Backend Application:** A Flask application organized by Blueprints that handles request routing, search heuristics, database querying, and HTML rendering.
- **Data Ingestion Engine:** A modular pipeline containing bulk downloaders and API clients. It handles fetching, parsing, canonicalizing, and deduplicating incident records across disparate aviation data sources.
- **Background Job System:** A Redis-backed queue (RQ) and worker process dedicated to handling long-running tasks, primarily durable LLM safety summary generation.
- **Database Layer:** A relational schema tracking Aircraft, Variants, Incidents, Sources, System Tags, and Import Logs.

### 4. Component Communication

- **Client to Backend:** Standard HTTP GET/POST requests. Interactive components use HTMX to issue AJAX requests and swap the returned HTML partials directly into the DOM.
- **Backend to Database:** Direct synchronous Python function calls translated into SQL queries by SQLAlchemy.
- **Backend to Background Worker:** The Flask web process enqueues tasks by writing job IDs to Redis. A separate RQ worker process consumes these jobs, executes the LLM calls, and updates the job status in the database.
- **Backend to External APIs:** Synchronous HTTP/REST requests using `httpx`. Resiliency is handled via the `tenacity` library to automatically apply exponential backoff and retries for rate limits and transient network errors.

### 5. Key Design Patterns

- **Model-View-Controller (MVC):** Clear separation of database schema (`models.py`), presentation logic (`templates/`), and business/routing logic (`routes.py`).
- **Template Method / Strategy Pattern:** The ingestion engine uses a base `DataSourceImporter` class that defines the core ingestion lifecycle (fetch, parse, deduplicate, upsert). Subclasses (like `NTSBImporter` or `FAASDRImporter`) implement the specific parsing logic for their respective domains.
- **Adapter Pattern:** The `ReportAnalyzerService` utilizes interchangeable adapters (`GeminiAnalyzerAdapter`, `DeepSeekAnalyzerAdapter`, `MockAnalyzerAdapter`) to present a unified interface for interacting with different LLM providers.
- **Asynchronous Job Pattern:** Offloading blocking I/O (such as AI API calls) from the main web thread to a durable message queue to ensure UI responsiveness and worker pool, ensuring the UI remains responsive and jobs survive process restarts.

