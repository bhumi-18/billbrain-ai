# BillBrain AI — Setup & Deployment Guide

> Your smart finance assistant that reads, understands, and organizes your bills instantly.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Setup](#local-setup)
3. [Configuration (Secrets)](#configuration-secrets)
4. [Running Tests](#running-tests)
5. [Deploy on Streamlit Community Cloud (Free)](#deploy-on-streamlit-community-cloud-free)
6. [Deploy on Railway (Free Tier)](#deploy-on-railway-free-tier)
7. [Deploy on Render (Free Tier)](#deploy-on-render-free-tier)
8. [Deploy on Vercel (via Python Serverless)](#deploy-on-vercel-via-python-serverless)
9. [Optional: Supabase (Cloud Database)](#optional-supabase-cloud-database)
10. [Optional: Google OAuth (Production Login)](#optional-google-oauth-production-login)
11. [Optional: Email Alerts (SMTP / SendGrid)](#optional-email-alerts-smtp--sendgrid)

---

## Prerequisites

- Python 3.10 or higher
- `pip` (comes with Python)
- A [Google AI Studio](https://aistudio.google.com/) account to get a Gemini API key
- Git

---

## Local Setup

### 1. Clone the repository

```bash
git clone https://github.com/your-username/billbrain-ai.git
cd billbrain-ai
```

### 2. Create a virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirement.txt
```

### 4. Create the secrets file

Streamlit reads secrets from `.streamlit/secrets.toml`. Create the file:

```bash
mkdir .streamlit
```

Then create `.streamlit/secrets.toml` with the following content:

```toml
# Required
GOOGLE_API_KEY = "your-gemini-api-key-here"

# Optional — defaults to "sqlite" if not set
STORAGE_BACKEND = "sqlite"   # or "supabase"

# Optional — only needed if using email alerts
EMAIL_BACKEND = "smtp"       # or "sendgrid"
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = "587"
SMTP_USER = "your-email@gmail.com"
SMTP_PASS = "your-app-password"

# Optional — only needed if using SendGrid
SENDGRID_API_KEY = "your-sendgrid-api-key"

# Optional — only needed if using Supabase
SUPABASE_URL = "https://your-project.supabase.co"
SUPABASE_KEY = "your-supabase-anon-key"
```

> **Never commit `.streamlit/secrets.toml` to Git.** Add it to `.gitignore`:
> ```
> .streamlit/secrets.toml
> ```

### 5. Get a Gemini API key

1. Go to [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
2. Click **Create API key**
3. Copy the key and paste it into `secrets.toml` as `GOOGLE_API_KEY`

### 6. Run the app

```bash
streamlit run app.py
```

The app opens at `http://localhost:8501`.

---

## Configuration (Secrets)

| Key | Required | Default | Description |
|---|---|---|---|
| `GOOGLE_API_KEY` | Yes | — | Gemini 2.5 Flash API key |
| `STORAGE_BACKEND` | No | `sqlite` | `sqlite` or `supabase` |
| `EMAIL_BACKEND` | No | `smtp` | `smtp` or `sendgrid` |
| `SMTP_HOST` | No | `smtp.gmail.com` | SMTP server host |
| `SMTP_PORT` | No | `587` | SMTP server port |
| `SMTP_USER` | No | — | SMTP sender email |
| `SMTP_PASS` | No | — | SMTP password or app password |
| `SENDGRID_API_KEY` | No | — | SendGrid API key |
| `SUPABASE_URL` | No | — | Supabase project URL |
| `SUPABASE_KEY` | No | — | Supabase anon/service key |

---

## Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with short traceback
pytest tests/ --tb=short

# Run a specific test file
pytest tests/test_extractor.py -v

# Run property-based tests with more examples (slower but more thorough)
pytest tests/ --hypothesis-seed=0
```

All 45 tests should pass. Tests cover all 18 correctness properties defined in the design spec.

---

## Deploy on Streamlit Community Cloud (Free)

This is the **recommended free deployment** for Streamlit apps — zero configuration, free HTTPS, and native secrets management.

### Steps

1. Push your code to a **public or private GitHub repository**

2. Go to [https://share.streamlit.io](https://share.streamlit.io) and sign in with GitHub

3. Click **New app**

4. Fill in:
   - **Repository**: `your-username/billbrain-ai`
   - **Branch**: `main`
   - **Main file path**: `app.py`

5. Click **Advanced settings** → **Secrets** and paste your secrets in TOML format:

```toml
GOOGLE_API_KEY = "your-gemini-api-key"
STORAGE_BACKEND = "sqlite"
```

6. Click **Deploy**

Your app will be live at `https://your-app-name.streamlit.app` in ~2 minutes.

> **Note on SQLite**: Streamlit Cloud has an ephemeral filesystem — the SQLite database (`billbrain.db`) resets on each redeploy. For persistent storage across sessions, use Supabase (see below).

---

## Deploy on Railway (Free Tier)

Railway offers a free tier with persistent storage, making it a good choice if you need the SQLite database to survive redeploys.

### Steps

1. Install the Railway CLI:
   ```bash
   npm install -g @railway/cli
   ```

2. Create a `Procfile` in the project root:
   ```
   web: streamlit run app.py --server.port=$PORT --server.address=0.0.0.0
   ```

3. Login and deploy:
   ```bash
   railway login
   railway init
   railway up
   ```

4. Set environment variables in the Railway dashboard under **Variables**:
   ```
   GOOGLE_API_KEY=your-gemini-api-key
   STORAGE_BACKEND=sqlite
   ```

5. Your app will be live at the Railway-provided URL.

> Railway's free tier includes 500 hours/month and 1GB persistent disk.

---

## Deploy on Render (Free Tier)

### Steps

1. Create a `render.yaml` in the project root:

```yaml
services:
  - type: web
    name: billbrain-ai
    env: python
    buildCommand: pip install -r requirement.txt
    startCommand: streamlit run app.py --server.port=$PORT --server.address=0.0.0.0
    envVars:
      - key: GOOGLE_API_KEY
        sync: false
      - key: STORAGE_BACKEND
        value: sqlite
```

2. Push to GitHub

3. Go to [https://render.com](https://render.com) → **New Web Service** → connect your GitHub repo

4. Render auto-detects `render.yaml` and configures the service

5. Add `GOOGLE_API_KEY` in the **Environment** tab

6. Click **Deploy**

> Render's free tier spins down after 15 minutes of inactivity. The first request after sleep takes ~30 seconds to wake up.

---

## Deploy on Vercel (via Python Serverless)

> **Important**: Vercel is designed for serverless functions and static sites. Streamlit apps are long-running processes and are **not natively supported** on Vercel's free tier. The recommended approach is to use Streamlit Community Cloud, Railway, or Render instead.
>
> If you still want to use Vercel, you can deploy a **FastAPI wrapper** that serves the app logic as an API, but the interactive Streamlit UI cannot run on Vercel directly.

### Alternative: Deploy the API layer on Vercel

If you want to expose BillBrain AI as a REST API (without the Streamlit UI) on Vercel:

1. Install FastAPI:
   ```bash
   pip install fastapi uvicorn python-multipart
   ```

2. Create `api/index.py`:
   ```python
   from fastapi import FastAPI, UploadFile, File
   from typing import List

   app = FastAPI()

   @app.get("/")
   def root():
       return {"message": "BillBrain AI API"}
   ```

3. Create `vercel.json`:
   ```json
   {
     "builds": [{"src": "api/index.py", "use": "@vercel/python"}],
     "routes": [{"src": "/(.*)", "dest": "api/index.py"}]
   }
   ```

4. Deploy:
   ```bash
   npm install -g vercel
   vercel
   ```

**For the full Streamlit UI, use Streamlit Community Cloud instead.**

---

## Optional: Supabase (Cloud Database)

Use Supabase instead of SQLite for persistent storage that survives redeploys.

### Steps

1. Go to [https://supabase.com](https://supabase.com) and create a free project

2. In the Supabase SQL editor, run:
   ```sql
   CREATE TABLE invoices (
       invoice_id TEXT PRIMARY KEY,
       user_id TEXT NOT NULL,
       filename TEXT,
       vendor TEXT,
       invoice_date TEXT,
       items TEXT,
       total_amount REAL,
       tax_amount REAL,
       due_date TEXT,
       currency TEXT DEFAULT 'INR',
       detected_language TEXT,
       confidence_overall TEXT,
       extracted_at TEXT,
       is_duplicate INTEGER DEFAULT 0,
       duplicate_of TEXT,
       deleted INTEGER DEFAULT 0
   );
   ```

3. Install the Supabase client:
   ```bash
   pip install supabase-py
   ```

4. Add to your secrets:
   ```toml
   STORAGE_BACKEND = "supabase"
   SUPABASE_URL = "https://your-project.supabase.co"
   SUPABASE_KEY = "your-anon-key"
   ```

> The `SupabaseBackend` class in `storage.py` is currently a stub. Full implementation requires wiring the `supabase-py` client — see the `SupabaseBackend` class in `storage.py` for the interface to implement.

---

## Optional: Google OAuth (Production Login)

The app ships with a **mock dev login** (enter any email). To enable real Google OAuth:

### Steps

1. Go to [Google Cloud Console](https://console.cloud.google.com/) → **APIs & Services** → **Credentials**

2. Create an **OAuth 2.0 Client ID** (Web application type)

3. Add your deployment URL to **Authorized redirect URIs**

4. Install the auth library:
   ```bash
   pip install streamlit-google-auth
   ```

5. Download your credentials JSON and save as `google_credentials.json` (do not commit this file)

6. In `auth.py`, replace the mock login form in the `login()` function with:
   ```python
   from streamlit_google_auth import Authenticate

   auth = Authenticate(
       secret_credentials_path="google_credentials.json",
       cookie_name="billbrain_auth",
       cookie_key=st.secrets["COOKIE_KEY"],
       redirect_uri=st.secrets["OAUTH_REDIRECT_URI"],
   )
   auth.check_authentification()
   if auth.is_connected():
       return {"user_id": auth.id, "email": auth.email, "name": auth.name}
   auth.login()
   return None
   ```

7. Add to secrets:
   ```toml
   COOKIE_KEY = "a-random-secret-string"
   OAUTH_REDIRECT_URI = "https://your-app-url.streamlit.app"
   ```

---

## Optional: Email Alerts (SMTP / SendGrid)

### Gmail SMTP Setup

1. Enable **2-Step Verification** on your Google account
2. Go to [https://myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
3. Generate an **App Password** for "Mail"
4. Add to secrets:
   ```toml
   EMAIL_BACKEND = "smtp"
   SMTP_HOST = "smtp.gmail.com"
   SMTP_PORT = "587"
   SMTP_USER = "your-email@gmail.com"
   SMTP_PASS = "your-16-char-app-password"
   ```

### SendGrid Setup

1. Sign up at [https://sendgrid.com](https://sendgrid.com) (free tier: 100 emails/day)
2. Create an API key under **Settings → API Keys**
3. Install:
   ```bash
   pip install sendgrid
   ```
4. Add to secrets:
   ```toml
   EMAIL_BACKEND = "sendgrid"
   SENDGRID_API_KEY = "SG.your-api-key"
   ```

---

## Project Structure

```
billbrain-ai/
├── app.py                  # Main Streamlit app
├── models.py               # Dataclasses (InvoiceRecord, etc.)
├── file_handler.py         # File upload & validation
├── gemini_client.py        # Gemini 2.5 Flash API client
├── extractor.py            # JSON parsing & confidence scoring
├── duplicate_checker.py    # Duplicate invoice detection
├── export_engine.py        # CSV & Excel export
├── dashboard_engine.py     # Spending analytics
├── storage.py              # SQLite / Supabase persistence
├── auth.py                 # Authentication (mock + OAuth-ready)
├── email_alerts.py         # Due-date email reminders
├── requirement.txt         # Python dependencies
├── tests/
│   ├── test_file_handler.py
│   ├── test_extractor.py
│   ├── test_duplicate_checker.py
│   ├── test_gemini_client.py
│   ├── test_export_engine.py
│   ├── test_dashboard_engine.py
│   └── test_examples.py
└── .streamlit/
    └── secrets.toml        # Local secrets (never commit)
```

---

## Quick Reference

| Platform | Free Tier | Persistent DB | Custom Domain | Best For |
|---|---|---|---|---|
| Streamlit Community Cloud | ✅ Always free | ❌ Ephemeral | ❌ | Quickest deploy |
| Railway | ✅ 500 hrs/mo | ✅ 1GB disk | ✅ | Persistent SQLite |
| Render | ✅ Limited | ❌ Ephemeral | ✅ | Simple deploys |
| Vercel | ✅ | ❌ | ✅ | API only (not Streamlit UI) |
| Supabase | ✅ 500MB DB | ✅ Cloud | N/A | Cloud DB backend |
