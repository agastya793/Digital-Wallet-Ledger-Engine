# =============================================================================
# Digital Wallet Ledger Engine — Makefile
# =============================================================================
# Developer shortcuts for common Docker and project commands.
# Usage: make <target>
# Run `make help` to see all available targets.
# =============================================================================

.PHONY: help up dev down logs shell db-shell migrate makemigrations \
        test lint format clean build rebuild

# Default target
.DEFAULT_GOAL := help

# ---- Colors ----
BLUE   := \033[0;34m
GREEN  := \033[0;32m
YELLOW := \033[1;33m
NC     := \033[0m

# =============================================================================
# Help
# =============================================================================
help: ## Show this help message
	@echo ""
	@echo "  $(BLUE)Digital Wallet Ledger Engine$(NC)"
	@echo "  ─────────────────────────────────"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-18s$(NC) %s\n", $$1, $$2}'
	@echo ""

# =============================================================================
# Docker — Production
# =============================================================================
up: ## Start all services (production mode)
	docker compose up -d

down: ## Stop all services
	docker compose down

build: ## Build Docker images
	docker compose build

rebuild: ## Force rebuild (no cache)
	docker compose build --no-cache

clean: ## Stop services + remove volumes (⚠ data loss)
	docker compose down -v --remove-orphans
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

# =============================================================================
# Docker — Development
# =============================================================================
dev: ## Start in development mode (hot reload)
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build

dev-d: ## Start in dev mode (detached)
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build

# =============================================================================
# Logs & Shell
# =============================================================================
logs: ## Tail application logs
	docker compose logs -f app

logs-all: ## Tail all service logs
	docker compose logs -f

shell: ## Open a shell in the app container
	docker compose exec app bash

db-shell: ## Open PostgreSQL interactive shell
	docker compose exec db psql -U postgres -d wallet_db

redis-cli: ## Open Redis CLI
	docker compose exec redis redis-cli

# =============================================================================
# Database Migrations
# =============================================================================
migrate: ## Run pending Alembic migrations
	docker compose exec app alembic upgrade head

makemigrations: ## Auto-generate a new migration
	@read -p "Migration message: " msg; \
	docker compose exec app alembic revision --autogenerate -m "$$msg"

rollback: ## Rollback last migration
	docker compose exec app alembic downgrade -1

# =============================================================================
# Testing & Quality
# =============================================================================
test: ## Run tests with coverage
	docker compose exec app pytest --cov=app --cov-report=term-missing

test-v: ## Run tests (verbose)
	docker compose exec app pytest -v --cov=app

lint: ## Run linter (ruff check)
	docker compose exec app ruff check app/ tests/

format: ## Auto-format code (ruff)
	docker compose exec app ruff format app/ tests/
	docker compose exec app ruff check --fix app/ tests/

# =============================================================================
# Local Development (without Docker)
# =============================================================================
install: ## Install dependencies locally
	pip install -e ".[dev,test]"

run: ## Run app locally (without Docker)
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# =============================================================================
# Status
# =============================================================================
ps: ## Show running containers
	docker compose ps

health: ## Check service health
	@echo "$(YELLOW)Checking services...$(NC)"
	@docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"
