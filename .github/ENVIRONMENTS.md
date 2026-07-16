# GitHub Environments setup for Vyuflo backend CI/CD
# Repo → Settings → Environments → create: dev, staging, pre-live, prod

## Per-environment secrets (add on EACH of the 4 environments)

| Secret | Example (dev) | Example (prod) |
|--------|---------------|----------------|
| `HOST` | `xxx.xxx.xxx.xxx` | prod droplet IP |
| `USER` | `root` | `deploy` |
| `SSH_KEY` | private key PEM | private key PEM |
| `DEPLOY_PATH` | `/opt/vyuflo-dev` | `/opt/vyuflo-prod` |
| `COMPOSE_FILE` | `docker-compose.dev.yml` | `docker-compose.prod.yml` |
| `DEPLOY_BRANCH` | `dev` | `main` |
| `GH_PAT` | GitHub PAT with `repo` scope (can also be a repository-level secret) | same |

Suggested `DEPLOY_BRANCH` values:
- **dev** → `dev`
- **staging** → `staging`
- **pre-live** → `pre-live`
- **prod** → `main`

## Server layout (per droplet)

```
/opt/vyuflo-<env>/
  docker-compose.<env>.yml   # copy from repo docker-compose.yml and rename
  backend/                   # git clone of this repo
    .env                     # app secrets — see .env.example
```

## Triggers

| Event | Workflow |
|-------|----------|
| Pull request → `dev`/`staging`/`pre-live`/`main` | `ci.yml` (compile + import smoke + Docker build) |
| Pull request opened/edited → same branches | `pr-lint.yml` (title + description conventions) |
| Push → `dev` / `staging` / `pre-live` / `main` | `deploy.yml` (CI then SSH deploy) |
| Actions → Deploy → Run workflow | Manual deploy to chosen environment |

PR title/body rules: see [`PULL_REQUESTS.md`](./PULL_REQUESTS.md).

## Protection rules (recommended)

- **pre-live** / **prod**: enable Required reviewers
- **prod**: restrict to `main` branch only
