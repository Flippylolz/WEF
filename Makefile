SHELL := /bin/sh

UV := uv
PNPM := pnpm
DOCKER := docker
COMPOSE := $(DOCKER) compose --file infra/compose.yaml
BACKEND := $(UV) --directory apps/backend run

.DEFAULT_GOAL := help

.PHONY: help install format format-check lint typecheck test contract-generate contract-check build build-development compose-config up down ps logs importer-dry-run seed-m1

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
		'make up                 Build and start the healthy local stack' \
		'make down               Stop containers while preserving data' \
		'make ps                 Show local service status' \
		'make logs               Follow recent local service logs' \
		'make importer-dry-run   Verify the read-only source mount' \
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

up: ## Build and start the healthy local stack.
	$(COMPOSE) up --build --detach --wait

down: ## Stop local containers without deleting persistent volumes.
	$(COMPOSE) down

ps: ## Show local Compose service status.
	$(COMPOSE) ps

logs: ## Follow recent local service logs.
	$(COMPOSE) logs --follow --tail=200

importer-dry-run: ## Verify that the configured source export is read-only.
	$(COMPOSE) --profile operator run --rm importer

seed-m1: ## Converge the invented local M1 fixture after migrations.
	$(COMPOSE) --profile operator run --rm seed
