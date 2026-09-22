# Don't Mess With The Don

Don't Mess With The Don (DMWTD) is a non-profit organization based in the GTA that focuses on environmental and community initiatives. DMWTD connects volunteers, residents, and local partners and hosts events, educational programs, and fundraising initiatives related to sustainability.

## The Problem

A lot of people register for volunteering events online but don't show up. This is a recurring problem — the actual output of volunteer efforts isn't living up to its potential.

## Our Solution

This project is built by [UW Blueprint](https://uwblueprint.org) to address this with a centralized event management portal. The platform streamlines event discovery, attendee registration and vetting, attendance tracking, and data reporting for both staff and community members.

## Stack

- **Backend:** Python (FastAPI + SQLModel)
- **Frontend:** React (TypeScript)
- **Database:** PostgreSQL
- **Infrastructure:** Docker

## Environment Setup

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- Node.js 18+ (install directly from [nodejs.org](https://nodejs.org/) or via [nvm](https://github.com/nvm-sh/nvm))

### Initial Setup

1. Clone this repository and `cd` into the project folder
2. Set up environment files:

   **Ask PL** To share `.env` (root) and `frontend/.env` and place them in the repo root and `frontend/` respectively.

3. Start all services:
```bash
docker-compose up --build
```

The backend runs at http://localhost:8080 and the frontend at http://localhost:3000.

### Python Backend

The backend uses **FastAPI** with **SQLModel** (SQLAlchemy + Pydantic). Database migrations are managed with Alembic and run automatically on container startup.

#### Generating a new migration

After modifying a model in `backend/python/app/models/`, generate a migration:

```bash
docker exec -it don-backend alembic revision --autogenerate -m "describe your change"
```

Alembic diffs your models against the current DB schema and writes the migration file to `backend/python/migrations/versions/`.

#### Running migrations manually

```bash
docker exec -it don-backend alembic upgrade head
```

### Seeding sample data (development & testing)

Sample data lives as plain CSV files in `backend/python/seeds/` — one file per
table (`event_types.csv`, `users.csv`, `events.csv`, `form_submissions.csv`,
`registrations.csv`, `attendance.csv`). To change what gets seeded, just edit
the CSVs; the header row of each file matches the model's field names.

Run the seeder against the running dev database (via the `make` shortcuts, with
the raw commands shown for reference):

```bash
# Seed only if the database is empty (safe to run anytime)
make seed          # docker exec -it don-backend python -m app.seed

# Wipe the seeded tables and reload them from the CSVs
make seed-reset    # docker exec -it don-backend python -m app.seed --reset

# Wipe and seed the test database instead of the dev database
make seed-test     # docker exec -it -e APP_ENV=testing don-backend python -m app.seed --reset
```

Run `make help` to see all available shortcuts (start/stop, migrations, linting,
tests, DB shell, etc.).

To seed automatically when the backend container starts, set `SEED_DB=true` in
the root `.env`. Startup seeding is off by default and idempotent — it skips if
the database already has data, so it is safe to leave enabled across restarts.

**CSV notes:**
- Blank cells fall back to the model default (usually `NULL`) — leave optional
  columns empty.
- Rows are inserted in file order, so list parents before children in
  `users.csv` (the `guardian_id` self-reference).
- JSON/array columns (`form_json`, `response_json`, `image_urls`, `notes`) must
  contain valid JSON, e.g. `{"waiver_required": true}` or `["a", "b"]`. Wrap
  those cells in double quotes and double any internal quotes (standard CSV
  quoting).

### Useful Commands

```bash
# List running containers
docker ps

# Open a shell in the backend container
docker exec -it don-backend /bin/bash

# Open a psql shell in the database container
docker exec -it don-db psql -U postgres -d postgres

# Lint Python code (check only)
docker exec don-backend ruff check .

# Auto-fix lint issues
docker exec don-backend ruff check --fix .

# Format Python code
docker exec don-backend ruff format .

# Check formatting without applying
docker exec don-backend ruff format --check .

# Type check
docker exec don-backend mypy .

# Run Python tests
docker exec -it don-backend pytest
```

## Version Control Guide

- Branch off `main` for all feature work. Use the format `your-name/short-description` (e.g. `pranav/readme-update`)
- Rebase onto `main` to integrate upstream changes (do not merge)
- Commits should be atomic and written in imperative tense (e.g. "Add volunteer registration endpoint")
