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
