# Pull request conventions

CI runs **PR Lint — Title & Description** on every PR targeting `dev`, `staging`, `pre-live`, or `main`.

To skip checks in rare cases, add the label `ignore-pr-lint` (use sparingly).

## Title format

Use [Conventional Commits](https://www.conventionalcommits.org/)-style titles:

```text
<type>: <short description>
<type>(<scope>): <short description>
```

Rules:

- **type** is required (see allowed list below)
- **scope** is optional (e.g. `auth`, `hr`, `ci`)
- subject must start with a **lowercase** letter
- keep the subject short and focused on *why* / *what*

### Allowed types

| Type | Use for |
|------|---------|
| `feat` | New feature or endpoint |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `style` | Formatting / lint-only (no logic change) |
| `refactor` | Code change that is not a fix or feature |
| `perf` | Performance improvement |
| `test` | Adding or updating tests |
| `build` | Dependencies, Docker, packaging |
| `ci` | GitHub Actions / CI config |
| `chore` | Maintenance that does not fit above |
| `revert` | Reverting a previous change |

### Good examples

```text
feat: add HR deadline list endpoint
feat(hr): support filtering deadlines by case
fix(auth): return 401 when refresh token is expired
docs: expand local setup README
ci: add PR title and description lint
chore: bump uvicorn to 0.32.0
```

### Bad examples

```text
Update stuff
Fixed bug
Feat: Add Login          # type must be lowercase; subject must start lowercase
FEAT: add login          # type casing
added new api            # missing type prefix
```

## Description format

GitHub pre-fills [`.github/pull_request_template.md`](./pull_request_template.md). Keep these sections:

```markdown
## Summary
- short bullets describing the change

## Test plan
- [ ] concrete steps you ran or expect reviewers to run
```

Both sections are required and must contain real content (not empty checkboxes / placeholders).
