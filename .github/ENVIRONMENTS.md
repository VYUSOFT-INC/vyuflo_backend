# GitHub Environments setup for Vyuflo backend CI/CD
# Repo → Settings → Environments → create: dev, staging, pre-live, prod

## Per-environment secrets (add on EACH of the 4 environments)

| Secret | Example (staging) | Example (prod) |
|--------|-------------------|----------------|
| `HOST` | `167.99.152.174` | prod droplet IP |
| `USER` | `root` | `deploy` |
| `SSH_KEY` | private key PEM (see below) | private key PEM |
| `DEPLOY_PATH` | `/opt/vyuflo-staging` | `/opt/vyuflo-prod` |
| `COMPOSE_FILE` | `docker-compose.staging.yml` | `docker-compose.prod.yml` |
| `DEPLOY_BRANCH` | `main` (fallback when branch is not passed) | `main` |
| `GH_PAT` | GitHub PAT with `repo` scope (can also be a repository-level secret) | same |

Suggested `DEPLOY_BRANCH` values (used as fallback only; manual deploys pick the branch in the workflow UI):
- **dev** → `dev`
- **staging** → `main` or `staging`
- **pre-live** → `pre-live`
- **prod** → `main`

## SSH key setup

1. Generate a deploy key pair (on your machine):
   ```bash
   ssh-keygen -t ed25519 -C "charan-visaflow-staging" -f ~/.ssh/vyuflo-staging-deploy -N ""
   ```
2. Add the **public** key to the server:
   ```bash
   ssh-copy-id -i ~/.ssh/vyuflo-staging-deploy.pub root@167.99.152.174
   ```
   Or append the public key line to `/root/.ssh/authorized_keys` on the droplet.
3. Add the **private** key to GitHub:
   - Repo → **Settings** → **Environments** → **staging** → **Environment secrets**
   - Name: `SSH_KEY`
   - Value: full contents of `vyuflo-staging-deploy` (the private key file, including `-----BEGIN/END-----` lines)

Public key fingerprint comment used for staging: `charan-visaflow-staging`.

Test SSH from your machine before relying on CI:
```bash
ssh -i ~/.ssh/vyuflo-staging-deploy root@167.99.152.174
```

## Server layout (per droplet)

```
/opt/vyuflo-<env>/
  docker-compose.<env>.yml   # copy from repo docker-compose.yml and rename
  backend/                   # git clone of this repo
    .env                     # app secrets — copy from .env.example (never commit)
```

Example staging bootstrap (one-time on the server):
```bash
ssh root@167.99.152.174
mkdir -p /opt/vyuflo-staging/backend
cd /opt/vyuflo-staging/backend
git clone -b main https://github.com/<org>/vyuflo_backend.git .
# create backend/.env from .env.example — never commit secrets
cd /opt/vyuflo-staging
# copy docker-compose.yml → docker-compose.staging.yml and adjust if needed
```

## App `.env` on each server

Create `backend/.env` from [`.env.example`](../.env.example) on the droplet. Set values per environment; do not copy secrets from another env or from git.

| Variable | dev / staging | pre-live / prod |
|----------|---------------|-----------------|
| `APP_ENV` | `dev` or `staging` | `pre-live` or `prod` |
| `DEBUG` | `true` (optional) | `false` |
| `SECRET_KEY` | long random string | long random string (unique per env) |
| `LOCAL_DATABASE_URL` | Postgres URL for that env | Postgres URL for that env |
| `REDIS_URL` | `redis://redis:6379/0` (Docker service name) | same |
| `STORAGE_BACKEND` | `local` or `s3` | usually `s3` |
| `CORS_ORIGINS` | frontend URL(s) for that env | production frontend URL(s) |
| `FRONTEND_URL` | e.g. `https://staging.example.com` | production app URL |
| `COOKIE_SECURE` | `true` when served over HTTPS | `true` |
| Integrations | `ANTHROPIC_API_KEY`, SMTP, OAuth, Stripe, Zoho — set only what that env uses | production keys only |

Local development uses the same keys; see [README.md](../README.md) for setup and `python -m uvicorn main:app --reload --port 8001`.

## Triggers

| Event | Workflow |
|-------|----------|
| Pull request → `dev`/`staging`/`pre-live`/`main` | `ci.yml` (compile + import smoke + Docker build) |
| Pull request opened/edited → same branches | `pr-lint.yml` (title + description conventions) |
| Push → `dev` / `staging` / `pre-live` / `main` | `deploy.yml` (CI then SSH deploy; branch = pushed branch) |
| Actions → Deploy → Run workflow | Manual deploy: pick **environment** + **branch** |

### Manual deploy (branch + environment)

1. GitHub → **Actions** → **Deploy** → **Run workflow**
2. **Target environment**: `dev`, `staging`, `pre-live`, or `prod`
3. **Git branch to deploy**: e.g. `main`, `staging`, `feature/my-branch`
4. Run — CI runs first, then SSH deploy to the selected environment

PR title/body rules: see [`PULL_REQUESTS.md`](./PULL_REQUESTS.md).

## Protection rules (recommended)

- **pre-live** / **prod**: enable Required reviewers
- **prod**: restrict to `main` branch only
