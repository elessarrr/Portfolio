# Deployment Guide - Aircraft Safety Tracker

This guide explains how to deploy the Aircraft Safety Tracker to **Railway**, a cloud platform that makes deployment easy.

## Prerequisites

- A [GitHub](https://github.com) account.
- A [Railway](https://railway.app) account (login with GitHub).
- The project code pushed to your GitHub repository.

## Step 1: Create a Project on Railway

1. Log in to [Railway dashboard](https://railway.app/dashboard).
2. Click **+ New Project**.
3. Select **Deploy from GitHub repo**.
4. Select your repository (`Portfolio`).
   - If it asks for permissions, grant access to the repository.
   - If your project is in a subdirectory (like `Aircraft Safety Tracker`), you'll configure that in the next step.

## Step 2: Configure the Service

1. Once the project is created, click on the service card (it will have your repo name).
2. Go to the **Settings** tab.
3. Scroll down to **Root Directory**.
   - Enter: `Aircraft Safety Tracker` (or `/Aircraft Safety Tracker`).
   - *Note: This is critical because your `Procfile` and `requirements.txt` are inside this folder, not at the root of the repo.*
4. Go to the **Variables** tab.
5. Add the following environment variables:
   - `FLASK_APP`: `run.py`
   - `FLASK_CONFIG`: `production`
   - `SECRET_KEY`: (Generate a random string, e.g., `openssl rand -hex 32`)
   - `GOOGLE_GEMINI_API_KEY`: (Your Gemini API key)

## Step 3: Database Setup (Optional but Recommended)

By default, the app will use a local SQLite database file. This works, but:
- Data will reset every time you redeploy (because Railway files are ephemeral).
- To keep data persistent, you should use a PostgreSQL database.

**To add PostgreSQL:**
1. In your Railway project view, click **+ New**.
2. Select **Database** -> **PostgreSQL**.
3. Railway will automatically add a `DATABASE_URL` variable to your main service.
   - *Our code is already set up to use this variable if present!*

**Migrating Data:**
Since we scraped data locally, the production database will be empty initially. You have two options:
1. **Run the scrapers in production:**
   - Use the Railway CLI or "Run Command" feature to run `python scripts/import_data.py`.
2. **Upload your local SQLite DB (Simpler for read-only apps):**
   - If you stick with SQLite, you need to mount a "Volume" in Railway to persist `data/aircraft_safety.db`.
   - Go to **Settings** -> **Service Domains** -> **Volumes**.
   - Mount `/app/data`.

## Step 4: Verify Deployment

1. Go to the **Deployments** tab to see the build log.
2. Once it says "Active", click the generated URL (usually `https://something-production.up.railway.app`).
3. Test the application:
   - Try searching for "Boeing".
   - Check if the AI summaries appear (might take a moment to generate if cache is empty).

## Troubleshooting

- **Build Failed:** Check the logs. Did it fail installing requirements? Ensure `requirements.txt` is correct.
- **Application Error:** Check the "Deploy Logs". 
  - If you see "ModuleNotFoundError", check the Root Directory setting.
- **Database Errors:** If using PostgreSQL, you might need to run `flask db upgrade` in the Railway console to create tables.
