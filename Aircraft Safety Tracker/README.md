# Aircraft Safety Tracker

A full-stack web application that aggregates aviation safety data, providing users with instant access to incident history and AI-generated safety summaries for various aircraft models.

## Features

- **Search & Autocomplete:** Instantly find aircraft models with a responsive search bar.
- **Incident History:** View detailed lists of past incidents, filterable by date and severity.
- **AI Summaries:** leveraging Google Gemini to generate concise safety overviews for each aircraft.
- **Interactive UI:** Built with Tailwind CSS and HTMX for a smooth, single-page-app feel without the complexity.
- **Mobile Responsive:** Fully optimized for desktop and mobile devices.

## Tech Stack

- **Backend:** Python, Flask, SQLAlchemy
- **Frontend:** HTML5, Tailwind CSS, HTMX, Jinja2
- **Database:** SQLite (Dev), PostgreSQL (Prod ready)
- **AI:** Google Gemini API
- **Testing:** Pytest

## Setup & Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd "Aircraft Safety Tracker"
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables:**
   Copy `.env.example` to `.env` and add your API keys.
   ```bash
   cp .env.example .env
   ```

5. **Initialize the database:**
   ```bash
   flask db upgrade
   python scripts/import_data.py
   ```

6. **Run the application:**
   ```bash
   flask run
   ```

## Deployment

This project includes a `Procfile` for easy deployment on platforms like Railway.
See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed instructions.

## License

MIT License
