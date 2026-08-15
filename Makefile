SHELL := /bin/sh

UV := uv
PNPM := pnpm
DOCKER := docker
COMPOSE := $(DOCKER) compose --file infra/compose.yaml
BACKEND := $(UV) --directory apps/backend run

.DEFAULT_GOAL := help

.PHONY: help install format format-check lint typecheck test contract-generate contract-check build build-development compose-config production-proof production-runtime-proof up down ps logs importer-dry-run seed-m1

help: ## List supported commands.
	@printf '%s\n' \
		'make install            Install frozen backend/frontend dependencies' \
		'make format             Format backend/frontend source' \
		'make format-check       Verify source formatting' \
		'make lint               Run backend/frontend and architecture lint' \
		'make typecheck          Run strict Python and TypeScript checks' \
		'make test               Run backend/frontend tests' \
		'make contract-generate  Export OpenAPI and generated TypeScript' \
		'make contract-check     Verify OpenAPI, generated types, and static docs' \
		'make build              Build production runtime images' \
		'make build-development  Build development images' \
		'make compose-config     Validate the local Compose model' \
		'make production-proof   Prove production topology and deployment safety' \
		'make production-runtime-proof  Recreate the isolated production runtime' \
		'make up                 Build and start the healthy local stack' \
		'make down               Stop containers while preserving data' \
		'make ps                 Show local service status' \
		'make logs               Follow recent local service logs' \
		'make importer-dry-run   Run the read-only historical parser report' \
		'make seed-m1            Converge the invented local M1 fixture'

install: ## Install frozen dependencies.
	$(UV) sync --project apps/backend --frozen
	$(PNPM) install --frozen-lockfile

format: ## Format source files.
	$(BACKEND) ruff format .
	$(PNPM) --filter web format

format-check: ## Verify source formatting.
	$(BACKEND) ruff format --check .
	$(PNPM) --filter web format:check

lint: ## Run code and architecture lint.
	$(BACKEND) ruff check .
	cd apps/backend && PYTHONPATH=src $(UV) run lint-imports --config ../../.importlinter
	$(PNPM) --filter web lint

typecheck: ## Run static type checks.
	$(BACKEND) mypy
	$(PNPM) --filter web typecheck

test: ## Run synthetic backend/frontend tests.
	@test_database_url="$${TEST_DATABASE_URL:-}"; \
	if [ -z "$$test_database_url" ] && [ -f .env ]; then \
		test_database_url="$$( \
			$(BACKEND) dotenv --file ../../.env get TEST_DATABASE_URL \
			2>/dev/null || true \
		)"; \
	fi; \
	if [ -z "$$test_database_url" ]; then \
		printf '%s\n' \
			'error: TEST_DATABASE_URL is required for make test.' \
			'Export it or add it to the ignored repository .env file.' >&2; \
		exit 2; \
	fi; \
	TEST_DATABASE_URL="$$test_database_url" \
		$(BACKEND) pytest --cov=wef_backend --cov-branch --cov-report=term-missing
	$(PNPM) --filter web test

contract-generate: ## Generate committed API contracts.
	$(BACKEND) wef-export-openapi
	$(PNPM) --filter web contract:generate

contract-check: ## Verify contract drift and offline docs.
	$(BACKEND) wef-export-openapi
	git diff --exit-code -- contracts/openapi/v1.json
	$(PNPM) --filter web contract:check
	$(PNPM) --filter web contract:lint
	$(PNPM) --filter web contract:docs

build: ## Build non-root runtime images.
	$(DOCKER) build --file apps/backend/Dockerfile --target runtime --tag wef-backend:local .
	$(DOCKER) build --file apps/web/Dockerfile --target runtime --tag wef-web:local .

build-development: ## Build development images.
	$(DOCKER) build --file apps/backend/Dockerfile --target development --tag wef-backend:development .
	$(DOCKER) build --file apps/web/Dockerfile --target development --tag wef-web:development .

compose-config: ## Validate the fully rendered local Compose model.
	$(COMPOSE) --profile operator config --quiet

production-proof: ## Prove production topology and deployment safety.
	python3 -m scripts.prove_production_topology
	python3 -m scripts.prove_deploy_rollback
	python3 -m scripts.prove_release_workflow
	for script in scripts/deploy/*.sh; do sh -n "$$script"; done
	shellcheck scripts/deploy/*.sh
	$(DOCKER) run --rm \
		--volume "$(CURDIR)/infra/Caddyfile.production:/etc/caddy/Caddyfile:ro" \
		--entrypoint caddy \
		caddy:2.10.2-alpine@sha256:4c6e91c6ed0e2fa03efd5b44747b625fec79bc9cd06ac5235a779726618e530d \
		validate --config /etc/caddy/Caddyfile --adapter caddyfile

production-runtime-proof: ## Recreate production services and prove persistence.
	python3 -m scripts.prove_production_runtime

up: ## Build and start the healthy local stack.
	$(COMPOSE) up --build --detach --wait

down: ## Stop local containers without deleting persistent volumes.
	$(COMPOSE) down

ps: ## Show local Compose service status.
	$(COMPOSE) ps

logs: ## Follow recent local service logs.
	$(COMPOSE) logs --follow --tail=200

importer-dry-run: ## Run the historical parser and write aggregate dry-run reports.
	$(COMPOSE) --profile operator run --rm importer

seed-m1: ## Converge the invented local M1 fixture after migrations.
	$(COMPOSE) --profile operator run --rm seed
