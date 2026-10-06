# Convenience shortcuts around docker compose.
# Run `make help` to list available targets.

BACKEND := don-backend
DB      := don-db

.DEFAULT_GOAL := help
.PHONY: help up down build rebuild logs restart \
        seed seed-reset seed-test \
        migrate migration \
        shell db \
        lint format typecheck check test

help: ## List available commands
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| sort \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

## --- Containers ---

up: ## Start all services (build if needed)
	docker compose up --build

down: ## Stop and remove all containers
	docker compose down

build: ## Build images without starting
	docker compose build

rebuild: ## Rebuild the backend image from scratch (no cache)
	docker compose build --no-cache py-backend

logs: ## Tail backend logs
	docker compose logs -f py-backend

restart: ## Restart the backend container
	docker compose restart py-backend

## --- Database seeding ---

seed: ## Seed the dev DB (skips if it already has data)
	docker exec -it $(BACKEND) python -m app.seed

seed-reset: ## Wipe the seeded tables and reload from the CSVs
	docker exec -it $(BACKEND) python -m app.seed --reset

seed-test: ## Wipe and seed the test DB
	docker exec -it -e APP_ENV=testing $(BACKEND) python -m app.seed --reset

## --- Migrations ---

migrate: ## Apply migrations up to head
	docker exec -it $(BACKEND) alembic upgrade head

migration: ## Autogenerate a migration: make migration m="describe change"
	@test -n "$(m)" || (echo "Usage: make migration m=\"describe change\"" && exit 1)
	docker exec -it $(BACKEND) alembic revision --autogenerate -m "$(m)"

## --- Shells ---

shell: ## Open a bash shell in the backend container
	docker exec -it $(BACKEND) /bin/bash

db: ## Open a psql shell in the dev database
	docker exec -it $(DB) psql -U postgres -d dmwtd

## --- Code quality ---

lint: ## Auto-fix lint issues (ruff)
	docker exec $(BACKEND) ruff check --fix .

format: ## Format Python code (ruff)
	docker exec $(BACKEND) ruff format .

typecheck: ## Run the type checker (mypy)
	docker exec $(BACKEND) mypy .

check: lint format typecheck ## Run lint, format, and typecheck

test: ## Run the backend test suite (pytest)
	docker exec -it $(BACKEND) pytest
