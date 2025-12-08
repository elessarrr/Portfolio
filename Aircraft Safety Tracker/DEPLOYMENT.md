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
   - *Note: This is critical because your `Procfile` and `requirements.txt` are inside this folder.*
4. Go to the **Variables** tab.
5. Add the following environment variables:
   - `FLASK_APP`: `run.py`
   - `FLASK_CONFIG`: `production`
   - `SECRET_KEY`: (Generate a random string, e.g., `openssl rand -hex 32`)
   - `DEEPSEEK_API_KEY`: (Your DeepSeek API key)

## Step 3: Database Setup

To keep data persistent, we will use a PostgreSQL database.

1. In your Railway project view, click **+ New**.
2. Select **Database** -> **PostgreSQL**.
3. Railway will automatically add a `DATABASE_URL` variable to your main service.
   - *Our code is already set up to use this variable if present!*

## Step 4: Initialize the Database

Since this is a new database, we need to create the tables and import the data.

1. **Deploy the changes**: Ensure your latest code (with `Procfile` and `config.py`) is pushed to GitHub. Railway should auto-deploy.
2. **Wait for deployment**: Check the **Deployments** tab. Wait until it says "Active".

### Option A: Using the Railway CLI (Recommended)
This is the cleanest way. Run these commands in your local terminal:
```bash
railway login
railway link (select your project)
railway run python scripts/import_data.py
```

### Option B: Using the Railway Web Console (No CLI)
If you prefer to stay in the browser:
1. Go to your service **Settings** tab.
2. Scroll to **Start Command**.
3. Change it from `gunicorn run:app` to:
   ```bash
   flask db upgrade && python scripts/import_data.py && gunicorn run:app
   ```
4. Click **Deploy** (or it might auto-deploy).
5. Watch the **Deploy Logs**. You should see it importing data.
6. Once deployed and verified, you can (optionally) change the Start Command back to just `gunicorn run:app` to speed up future restarts.

## Step 5: Verify Deployment

1. Go to the **Deployments** tab.
2. Click the generated URL (usually `https://something-production.up.railway.app`).
3. Test the application:
   - Try searching for "Boeing".
   - Check if the AI summaries appear.

## Troubleshooting

- **Application Error:** Check the "Deploy Logs".
  - If you see "ModuleNotFoundError", check the Root Directory setting.
- **Database Errors:** Ensure `DATABASE_URL` is present and you ran `flask db upgrade`.
