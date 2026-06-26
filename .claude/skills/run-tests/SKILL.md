---
name: run-tests
description: Run the test suites (backend pytest and e2e), iterate on failures by fixing and re-running, and flag remaining failures with a clear summary. Use when asked to run tests, check what's broken, or iterate to green.
---

# run-tests

Run the project's tests, fix what's straightforwardly fixable, and clearly flag anything
left broken. The backend runs in Docker, so make sure the stack is up first:
`docker compose up -d`. The compose service is **`py-backend`**.

## What to run

### Backend unit + functional tests (default)

```bash
docker compose exec py-backend pytest
```

Narrow scope while iterating with the usual pytest selectors, e.g.
`docker compose exec py-backend pytest tests/unit -x -q` or
`... pytest tests/functional/test_foo.py::test_bar`.

### End-to-end tests (when asked, or when backend behavior/contracts changed)

These live in `e2e-tests/` and hit the **running** stack, so the app must be up
(`docker compose up -d`) before running them. They take options defined in
`e2e-tests/conftest.py`:

- `--api rest` (default) or `--api graphql`
- `--auth` to exercise auth flows
- `--fs` to exercise file-upload flows
- `--lang ts` (default) or `--lang python`

```bash
# from the e2e-tests/ directory, against the live stack
pytest e2e-tests
pytest e2e-tests --api graphql
pytest e2e-tests --auth --fs
```

When in doubt about which suites to run, ask the user which they want before grinding
through everything.

## Iterate

1. Run the relevant suite.
2. For each failure, read the traceback and the test, and decide:
   - **Clear bug in code or test** → fix it, then re-run just that test to confirm.
   - **Ambiguous / behavior change / needs a product decision** → don't guess; flag it.
3. Re-run the narrowed scope until green, then re-run the full suite once at the end to
   make sure nothing regressed.
4. Prefer `-x` (stop on first failure) and a single test path while iterating to keep
   the loop fast; widen back out once it's passing.

## Flag feedback

Always end with a short, scannable summary:

- ✅ **Passing**: suites/counts that are green.
- 🔧 **Fixed**: what you changed and why (one line each).
- 🚩 **Needs attention**: failures you did NOT fix, each with the test name, the gist of
  the failure, and why you left it (ambiguous expectation, missing fixture/data, product
  decision needed, flaky, env issue, etc.).

Be honest about what's still red — never report green unless the run actually passed.

## Notes

- If `docker compose exec` errors with "no such service", the stack isn't up — run
  `docker compose up -d` and retry.
- Frontend tests (`react-scripts test`) exist but are interactive/watch-based; only run
  them if the user explicitly asks.
- Before pushing, also run `/prep-commit` for lint/format/type checks.
