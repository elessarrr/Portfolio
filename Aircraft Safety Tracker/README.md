// ... existing code ...

# Aircraft Safety Tracker

**A full-stack web application leveraging GenAI for aviation safety analysis.**

[View Source on GitHub (v2 Branch)](https://github.com/elessarrr/Portfolio/tree/v2-%28first-round-of-feedback-from-RJ%29/Aircraft%20Safety%20Tracker)

---

## 📖 Executive Summary

The **Aircraft Safety Tracker** is a proof-of-concept (POC) application designed to aggregate aviation safety data. By collecting historical incident logs and applying **Generative AI (Google Gemini)**, the system transforms raw data into concise summaries. This tool helps users assess aircraft safety profiles by providing context to safety events beyond simple statistics.

This project serves as a demonstration of **Full-Stack Engineering**, **Data Pipelines**, and **Applied AI** integration within a modular architecture.

---

## 🚀 Key Features

*   **AI-Powered Summaries**: Integrates **Google Gemini** to synthesize incident reports into readable safety assessments.
*   **Data Ingestion**: Python scripts that scrape, clean, and normalize data from the Aviation Safety Network.
*   **Efficient Search**: Fuzzy-search capabilities powered by PostgreSQL's `pg_trgm` extension for quick retrieval of aircraft models.
*   **Interactive Interface**: Dynamic filtering of incidents by date, severity, and type in a responsive UI.
*   **Modern Stack**: Built with **HTMX** and **Tailwind CSS** to deliver a responsive experience with server-side rendering.

---

## 🏗 System Architecture

The application is structured as a modular Monolith, separating concerns for maintainability.

### **1. Data Layer**
*   **Database**: **PostgreSQL** (Production) / SQLite (Dev) managed via **SQLAlchemy ORM**.
*   **Migrations**: Database schema version control using **Alembic (Flask-Migrate)**.
*   **Caching**: Redis/SimpleCache implementation to optimize frequent queries.

### **2. Application Layer (Backend)**
*   **Framework**: **Flask** (Python) utilizing the **Application Factory Pattern** for configuration management.
*   **AI Service**: Encapsulated service layer for LLM interactions with error handling.
*   **Background Jobs**: Scripts for scraping and data ingestion using `httpx` and `BeautifulSoup`.

### **3. Presentation Layer (Frontend)**
*   **Templating**: **Jinja2** for server-side rendering.
*   **Interactivity**: **HTMX** for AJAX-driven updates (search, pagination) without heavy client-side frameworks.
*   **Styling**: **Tailwind CSS** for utility-first UI development.

---

## 🛠 Technical Highlights

*   **Robust Scraping**: The scraping engine handles rate limiting, network timeouts, and parsing errors to ensure consistent data collection.
*   **Modular Codebase**: Organized into Blueprints and Services to separate business logic (e.g., `GeminiService`) from HTTP routing.
*   **Deployment**: Includes `Procfile` for PaaS deployment and environment variable configuration.
*   **Testing**: Unit and integration tests using `pytest` to ensure reliability of core functions.

---

## 🔮 Future Roadmap

*   **Predictive Analytics**: Implementing time-series forecasting to predict safety trends.
*   **API Exposure**: Developing a RESTful API for third-party integrations.
*   **Multi-Model AI Support**: Abstraction layer to support OpenAI GPT-4 and Anthropic Claude alongside Gemini.
*   **Real-time Alerts**: Email/SMS notifications for new incidents involving tracked aircraft.

---

## 💻 Local Development Setup

For engineers looking to run the project locally:

1.  **Clone & Install**:
    ```bash
    git clone -b v2-(first-round-of-feedback-from-RJ) https://github.com/elessarrr/Portfolio.git
    cd "Portfolio/Aircraft Safety Tracker"
    python -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```

2.  **Configuration**:
    *   Copy `.env.example` to `.env`.
    *   Add your `GOOGLE_GEMINI_API_KEY`.
    *   Add `AUTO_SEED=true` to your `.env` file.
    
    > **Note:** `AUTO_SEED=true` enables automatic data bootstrapping. If your local database is empty upon starting the server, it will automatically populate with synthetic fixture data. Unset this variable or set it to `false` to disable auto-seeding. Do **NOT** use `AUTO_SEED=true` in production.

3.  **Initialize Data**:
    ```bash
    flask db upgrade
    python scripts/import_data.py
    ```

4.  **Run**:
    ```bash
    flask run
    ```

---

## 📄 License

MIT License. Open for contribution and educational use.