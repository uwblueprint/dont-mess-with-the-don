#!/bin/sh
set -e

cd /app

# Apply database migrations.
alembic upgrade head

# Optionally seed sample data on startup. Off by default; enable by setting
# SEED_DB=true in the environment (e.g. in the root .env for local dev).
# The seed script is idempotent: it skips seeding if the database already has
# data, so it is safe to leave enabled across container restarts.
if [ "${SEED_DB:-false}" = "true" ]; then
  echo "SEED_DB=true -> seeding database with sample data"
  python -m app.seed
fi

exec python server.py
