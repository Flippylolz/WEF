SHELL := /bin/sh

UV := uv
PNPM := pnpm
DOCKER := docker
BACKEND := $(UV) --directory apps/backend run

.DEFAULT_GOAL := help

.PHONY: help install format format-check lint typecheck test contract-generate contract-check build build-development

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
		'make build-development  Build development images'

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
