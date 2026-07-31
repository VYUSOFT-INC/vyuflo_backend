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

## 2. Python virtual environment and dependencies

Use **Python 3.11** (matches CI and Docker). A **virtual environment** (`venv`) keeps this project’s packages isolated from the rest of your machine.

From the project root:

```bash
# Install Python 3.11 if needed (macOS)
brew install python@3.11

# Recreate venv (first time, or after switching Python version)
rm -rf venv
python3.11 -m venv venv
source venv/bin/activate

# Windows (PowerShell): .\venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

When the venv is active, your prompt usually starts with `(venv)`. Leave it with `deactivate`.

---

## 3. Set up PostgreSQL

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

## 4. (Optional) Start Redis

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

## 5. Create your `.env` file

The app loads settings from a file named `.env` in the project root. **Never commit real secrets.**

```bash
# Copy the example file
cp .env.example .env
```

Open `.env` in any editor and fill in values for your machine. All keys are listed in `.env.example`; use placeholders for integrations you are not testing yet.

### Key local settings

| Variable | Local dev notes |
|----------|-----------------|
| `APP_ENV` | `local` |
| `DEBUG` | `true` |
| `SECRET_KEY` | Any long random string |
| `DATABASE_ENV` | `local` |
| `LOCAL_DATABASE_URL` | Your Postgres URL (see below) |
| `REDIS_URL` | `redis://localhost:6379/0` |
| `STORAGE_BACKEND` | `local` (files go under `./uploads`) |
| `CORS_ORIGINS` | Include your frontend origin(s), e.g. `["http://localhost:3000"]` |
| `COOKIE_SECURE` | `false` on local HTTP |
| `ANTHROPIC_API_KEY`, Zoho, SMTP, OAuth, Stripe | Required keys exist in `.env.example`; empty placeholders are fine until you need those features |

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

## 6. Start the backend server

Make sure:

1. Your virtual environment is activated (`(venv)` in the prompt).
2. Postgres is running and the database exists.
3. `.env` is filled in.
4. You are in the project root (same folder as `main.py`).

Then run:

```bash
python -m uvicorn main:app --reload --port 8001
```

What this means:

| Piece | Meaning |
|-------|---------|
| `python -m uvicorn` | Runs Uvicorn with the same Python as your venv |
| `main:app` | Load `app` from `main.py` |
| `--reload` | Restart automatically when you change code (dev only) |
| `--port 8001` | API available on port 8001 |

On first start, the app:

1. Connects to Postgres
2. Creates missing tables automatically
3. Seeds base data (roles, visa types, document types, plans, etc.)

You should see logs similar to `Starting application...`.

---

## 7. Verify it works

Open these URLs in your browser:

| URL | What you should see |
|-----|---------------------|
| [http://localhost:8001/health](http://localhost:8001/health) | `{"status":"ok","version":"..."}` |
| [http://localhost:8001/docs](http://localhost:8001/docs) | Interactive Swagger API docs |
| [http://localhost:8001/redoc](http://localhost:8001/redoc) | Alternative API docs |

If `/health` returns OK, the server is running.

---

## Day-to-day workflow (quick checklist)

Every time you come back to work on this project:

```bash
cd vyuflo_backend
source venv/bin/activate          # Windows: .\venv\Scripts\Activate.ps1
python -m uvicorn main:app --reload --port 8001
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
http://localhost:8001
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

### Port 8001 already in use

Pick another port, for example:

```bash
python -m uvicorn main:app --reload --port 8002
```

Then open `http://localhost:8002/docs`.

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
