# VisaFlow Backend

VisaFlow is a FastAPI backend for visa application management (auth, documents, applications, HR, attorney, and admin APIs).

This guide walks you through running the API on your machine, even if you are new to Python.

---

## What you need (prerequisites)

Install these before starting:

| Tool | Why you need it | Suggested version |
|------|-----------------|-------------------|
| **Git** | Clone this repository | Any recent version |
| **Python** | Runs the backend | **3.11** (matches CI/Docker) |
| **PostgreSQL** | Main database | 14+ |
| **Redis** (optional for many local flows) | Caching / future session store | 7+ |
| **pip** | Installs Python packages | Comes with Python |

### Check that tools are installed

Open a terminal (macOS: Terminal / iTerm; Windows: PowerShell or Git Bash) and run:

```bash
python3 --version
# Expect something like: Python 3.11.x

psql --version
# Expect PostgreSQL client version output

redis-cli --version
# Optional — only if you install Redis
```

If `python3` is not found, install Python 3.11 from [python.org](https://www.python.org/downloads/) or via Homebrew on macOS:

```bash
brew install python@3.11
```

---

## 1. Get the code

```bash
git clone <YOUR_REPO_URL>
cd vyuflo_backend
```

You should see files like `main.py`, `requirements.txt`, and the `app/` folder.

---

## 2. Create a Python virtual environment

A **virtual environment** (`venv`) is an isolated folder of Python packages for this project only. It avoids breaking other projects on your machine.

From the project root:

```bash
# Create the virtual environment (one-time)
python3 -m venv venv

# Activate it (do this every time you open a new terminal for this project)
# macOS / Linux:
source venv/bin/activate

# Windows (PowerShell):
# .\venv\Scripts\Activate.ps1
```

When it is active, your prompt usually starts with `(venv)`.

To leave the virtual environment later:

```bash
deactivate
```

---

## 3. Install Python dependencies

With the virtual environment **activated**:

```bash
# Upgrade the package installer
python -m pip install --upgrade pip

# Install everything this project needs
pip install -r requirements.txt
```

This reads `requirements.txt` and installs FastAPI, Uvicorn, SQLAlchemy, and other libraries. It can take a few minutes the first time.

---

## 4. Set up PostgreSQL

The app expects a PostgreSQL database. Create one (name can be `vyuflo` or anything you prefer).

### Example with `psql`

```bash
# Start a Postgres shell (method depends on how you installed Postgres)
psql postgres

# Inside psql:
CREATE USER vyuflo WITH PASSWORD 'vyuflo';
CREATE DATABASE vyuflo OWNER vyuflo;
\q
```

Notes:

- On macOS with Homebrew, Postgres often runs as a background service after `brew install postgresql@16`.
- On Windows, use pgAdmin or the installer from [postgresql.org](https://www.postgresql.org/download/).
- You can also use Docker for Postgres only:

```bash
docker run --name vyuflo-postgres \
  -e POSTGRES_USER=vyuflo \
  -e POSTGRES_PASSWORD=vyuflo \
  -e POSTGRES_DB=vyuflo \
  -p 5432:5432 \
  -d postgres:16
```

---

## 5. (Optional) Start Redis

Redis is configured in the project. For many local auth flows the app can run with an in-memory store, but having Redis running matches production more closely.

```bash
# macOS (Homebrew)
brew install redis
brew services start redis

# Or with Docker
docker run --name vyuflo-redis -p 6379:6379 -d redis:7-alpine
```

Default URL used by the app: `redis://localhost:6379/0`

---

## 6. Create your `.env` file

The app loads settings from a file named `.env` in the project root. **Never commit real secrets.**

```bash
# Copy the example file
cp .env.example .env
```

Open `.env` in any editor and set at least the values below for local development.

### Minimum local settings

```env
# App
APP_NAME=VisaFlow
APP_VERSION=1.0.0
DEBUG=true
SECRET_KEY=local-dev-secret-change-me-to-something-long

# Database — use "local" while developing
DATABASE_ENV=local
LOCAL_DATABASE_URL=postgresql+asyncpg://vyuflo:vyuflo@localhost:5432/vyuflo
ZOHO_DATABASE_URL=postgresql+asyncpg://vyuflo:vyuflo@localhost:5432/vyuflo

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Storage — "local" saves files under ./uploads (good for local dev)
STORAGE_BACKEND=local
AWS_ACCESS_KEY_ID=local-placeholder
AWS_SECRET_ACCESS_KEY=local-placeholder
AWS_REGION=us-east-1
S3_BUCKET=local-placeholder

# CORS / cookies — allow your local frontend
CORS_ORIGINS=["http://localhost:3000","http://localhost:5173"]
COOKIE_SECURE=false
FRONTEND_URL=http://localhost:3000

# Required by config (placeholders are fine if you are not using these features yet)
ANTHROPIC_API_KEY=local-placeholder
ZOHO_CLIENT_ID=local-placeholder
ZOHO_CLIENT_SECRET=local-placeholder
ZOHO_REFRESH_TOKEN=local-placeholder
ZOHO_ORG_ID=local-placeholder
ZOHO_WORKSPACE_ID=local-placeholder

# Email / OAuth — leave empty until you need them
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=
SMTP_PASSWORD=
SMTP_FROM_EMAIL=noreply@visaflow.com
MAIL_STARTTLS=true
MAIL_SSL_TLS=false
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
MICROSOFT_CLIENT_ID=
MICROSOFT_CLIENT_SECRET=
APPLE_CLIENT_ID=
```

### How to read `LOCAL_DATABASE_URL`

Format:

```text
postgresql+asyncpg://USERNAME:PASSWORD@HOST:PORT/DATABASE_NAME
```

Example:

```text
postgresql+asyncpg://vyuflo:vyuflo@localhost:5432/vyuflo
```

| Part | Meaning |
|------|---------|
| `postgresql+asyncpg` | Driver used by this async FastAPI app (keep this prefix) |
| `vyuflo` (user) | Postgres username |
| `vyuflo` (password) | Postgres password |
| `localhost` | Database on your machine |
| `5432` | Default Postgres port |
| `vyuflo` (db name) | Database name |

If your password contains special characters (`@`, `#`, `/`, etc.), URL-encode them.

---

## 7. Start the backend server

Make sure:

1. Your virtual environment is activated (`(venv)` in the prompt).
2. Postgres is running and the database exists.
3. `.env` is filled in.
4. You are in the project root (same folder as `main.py`).

Then run:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

What this means:

| Piece | Meaning |
|-------|---------|
| `uvicorn` | ASGI server that runs FastAPI |
| `main:app` | Load `app` from `main.py` |
| `--reload` | Restart automatically when you change code (dev only) |
| `--host 0.0.0.0` | Listen on all interfaces |
| `--port 8000` | API available on port 8000 |

On first start, the app:

1. Connects to Postgres
2. Creates missing tables automatically
3. Seeds base data (roles, visa types, document types, plans, etc.)

You should see logs similar to `Starting application...`.

---

## 8. Verify it works

Open these URLs in your browser:

| URL | What you should see |
|-----|---------------------|
| [http://localhost:8000/health](http://localhost:8000/health) | `{"status":"ok","version":"..."}` |
| [http://localhost:8000/docs](http://localhost:8000/docs) | Interactive Swagger API docs |
| [http://localhost:8000/redoc](http://localhost:8000/redoc) | Alternative API docs |

If `/health` returns OK, the server is running.

---

## Day-to-day workflow (quick checklist)

Every time you come back to work on this project:

```bash
cd vyuflo_backend
source venv/bin/activate          # Windows: .\venv\Scripts\Activate.ps1
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Stop the server with `Ctrl + C`.

---

## Project layout (high level)

```text
vyuflo_backend/
├── main.py                 # App entry point (FastAPI + routers)
├── requirements.txt        # Python package list
├── .env.example            # Template for environment variables
├── .env                    # Your local secrets (do not commit)
├── alembic.ini             # Migration tool config (Alembic)
├── app/
│   ├── core/               # Config, database, auth, middleware
│   ├── models/             # Database models
│   ├── routes/             # HTTP endpoints (employee / admin / attorney / hr)
│   ├── schemas/            # Request/response shapes
│   └── services/           # Business logic
└── uploads/                # Local file uploads when STORAGE_BACKEND=local
```

API routes are mostly under the `/api/v1/...` prefix.

---

## Connecting a frontend

Point your frontend at:

```text
http://localhost:8000
```

Ensure `CORS_ORIGINS` in `.env` includes your frontend origin (for example `http://localhost:3000` or `http://localhost:5173`), and keep `COOKIE_SECURE=false` on local HTTP.

---

## Common problems

### `ModuleNotFoundError` or import errors

- Activate the virtual environment first.
- Re-run `pip install -r requirements.txt`.
- Run commands from the project root (where `main.py` lives).

### Database connection errors

- Confirm Postgres is running.
- Check username, password, host, port, and database name in `LOCAL_DATABASE_URL`.
- Confirm `DATABASE_ENV=local`.

### `ValidationError` / missing settings on startup

Some settings are required by `app/core/config.py`. If the app complains about a missing field, add that key to `.env` (placeholders are fine for unused integrations).

### Port 8000 already in use

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8001
```

Then open `http://localhost:8001/docs`.

### `command not found: uvicorn`

Virtual environment is not activated, or dependencies were not installed. Activate `venv` and run `pip install -r requirements.txt` again.

### Uploads / file features fail

Set `STORAGE_BACKEND=local` and ensure the `uploads/` folder exists (created automatically in Docker; locally you can `mkdir -p uploads` if needed).

---

## Optional: run with Docker

If you prefer containers (and already have Docker Desktop):

```bash
# Build the image from this repo
docker build -t vyuflo-backend .

# Run (still needs Postgres reachable and a .env file)
docker run --env-file .env -p 8000:8000 vyuflo-backend
```

The included `docker-compose.yml` is oriented toward server layouts (backend + Redis). For local day-to-day development, the **venv + uvicorn** flow above is usually simpler.

---

## Tech stack (for context)

- **FastAPI** — web API framework
- **Uvicorn** — server that runs FastAPI
- **SQLAlchemy + asyncpg** — async Postgres access
- **Pydantic Settings** — loads `.env` into typed config
- **Redis** — optional / production-oriented caching
- **AWS S3** — file storage in non-local environments (`STORAGE_BACKEND=s3`)

---

## Pull requests

CI validates PR **titles** and **descriptions** on every pull request.

- Title format: `feat: …`, `fix(auth): …`, `docs: …`, etc.
- Description must include `## Summary` and `## Test plan`

Full rules: [`.github/PULL_REQUESTS.md`](.github/PULL_REQUESTS.md)
