---
name: prep-commit
description: Run all lint, format, and type checks (and auto-fix) before pushing, exactly mirroring CI. Use before committing/pushing in this repo so nobody has to keep re-running ruff/mypy/eslint by hand.
---

# prep-commit

Get the working tree green **before** pushing so CI (`.github/workflows/lint.yml`) passes
on the first try. This runs the auto-fixers, then re-runs the exact checks CI gates on
and confirms they pass.

The backend runs inside Docker. The compose service is **`py-backend`** (not `backend`)
and the frontend service is **`frontend`**. Make sure the stack is up first:
`docker compose up -d`.

## Steps

Run these in order. If a fixer changes files, that's expected — the goal is a clean tree.

### 1. Backend — ruff lint + autofix

```bash
docker compose exec py-backend ruff check --fix .
```

### 2. Backend — ruff format

`ruff format` is a **separate** gate from `ruff check` (CI runs `ruff format --check .`).
Running the formatter here is what keeps that green:

```bash
docker compose exec py-backend ruff format .
```

### 3. Backend — mypy

mypy has no autofix; report any errors to the user and fix them before continuing.

```bash
docker compose exec py-backend mypy .
```

### 4. Frontend — eslint + autofix

CI lints the frontend too, so don't skip it:

```bash
docker compose exec frontend yarn fix
```

## Verify (re-run the exact CI checks)

After fixers run, confirm the tree is green the same way CI does:

```bash
docker compose exec py-backend ruff check .
docker compose exec py-backend ruff format --check .
docker compose exec py-backend mypy .
docker compose exec frontend yarn lint
```

All four must pass. If `ruff check` or `ruff format --check` still fails after the
fixers ran, surface the output — it usually means a fix needs manual attention.

## Wrap up

- Summarize what was changed (files reformatted, lint fixes applied) and confirm all
  checks are green.
- If any files were modified by the fixers, remind the user to `git add` / review them
  before committing.

## Notes

- Tests are **not** part of the CI lint gate, so this skill doesn't run them. To check
  manually: `docker compose exec py-backend pytest` (unit + functional in
  `backend/python/tests`), plus `e2e-tests/` if relevant.
- If `docker compose exec` errors with "no such service", the stack isn't up — run
  `docker compose up -d` and retry.
