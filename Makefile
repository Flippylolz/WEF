SHELL := /bin/sh

UV := uv
PNPM := pnpm
DOCKER := docker
COMPOSE := $(DOCKER) compose --file infra/compose.yaml
BACKEND := $(UV) --directory apps/backend run

.DEFAULT_GOAL := help

.PHONY: help install format format-check lint typecheck test coverage contract-generate contract-check build build-development compose-config production-proof production-runtime-proof shared-edge-proof up down ps logs importer-dry-run import-dry-run import-persist import-geocode import-media import-verify import-run seed-m1

IMPORT_BATCH_SIZE ?= 200
IMPORT_GEOCODE_BATCH_SIZE ?= 25
IMPORT_MAX_PROVIDER_REQUESTS ?= 500
IMPORTER := $(COMPOSE) --profile operator run --rm historical-importer \
	--batch-size $(IMPORT_BATCH_SIZE) \
	--geocode-batch-size $(IMPORT_GEOCODE_BATCH_SIZE) \
	--max-provider-requests $(IMPORT_MAX_PROVIDER_REQUESTS)

help: ## List supported commands.
	@printf '%s\n' \
		'make install            Install frozen backend/frontend dependencies' \
		'make format             Format backend/frontend source' \
		'make format-check       Verify source formatting' \
		'make lint               Run backend/frontend and architecture lint' \
		'make typecheck          Run strict Python and TypeScript checks' \
		'make test               Run backend/frontend tests' \
		'make coverage           Run tests and refresh the repository coverage badge' \
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
		'make import-dry-run     Preview exact new/changed rows and pending work' \
		'make import-persist     Persist new/changed source rows in batches' \
		'make import-geocode     Resume cache-first quota-aware geocoding' \
		'make import-media       Resume verified media copy and derivatives' \
		'make import-verify      Reconcile one exact source import' \
		'make import-run         Run all resumable import stages' \
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
	$(COMPOSE) --profile test up --detach --wait db
	$(COMPOSE) --profile test run --rm --no-deps test-db-reset
	$(COMPOSE) --profile test run --rm --no-deps --build backend-test
	$(COMPOSE) --profile test run --rm --no-deps --build frontend-test

coverage: ## Run branch-aware coverage and refresh the README badge.
	mkdir -p "$(CURDIR)/tmp/coverage/backend" "$(CURDIR)/tmp/coverage/frontend"
	$(COMPOSE) --profile test up --detach --wait db
	$(COMPOSE) --profile test run --rm --no-deps test-db-reset
	$(COMPOSE) --profile test run --rm --no-deps --build \
		--volume "$(CURDIR)/tmp/coverage/backend:/coverage" \
		backend-test pytest --cov=wef_backend --cov-branch \
		--cov-report=json:/coverage/coverage.json --cov-report=term-missing
	$(COMPOSE) --profile test run --rm --no-deps --build \
		--volume "$(CURDIR)/tmp/coverage/frontend:/coverage" \
		frontend-test pnpm test:coverage --coverage.reportsDirectory=/coverage/report
	python3 scripts/render_coverage_badge.py \
		--backend tmp/coverage/backend/coverage.json \
		--frontend tmp/coverage/frontend/report/coverage-summary.json \
		--output .github/badges/coverage.svg

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
	WEF_SHARED_EDGE_ROOT=/tmp/wef-edge-proof/root \
		WEF_SHARED_EDGE_FIXTURES=$(CURDIR)/infra/nginx/fixtures \
		WEF_EDGE_HTTP_PORT=18080 WEF_EDGE_HTTPS_PORT=18443 \
		$(COMPOSE) --file infra/compose.shared-edge.yaml \
		--file infra/compose.shared-edge-fixtures.yaml --profile renew config --quiet

production-proof: ## Prove production topology and deployment safety.
	python3 -m scripts.prove_production_topology
	python3 -m scripts.prove_deploy_rollback
	python3 -m scripts.prove_release_workflow
	$(MAKE) shared-edge-proof
	for script in scripts/deploy/*.sh; do sh -n "$$script"; done
	shellcheck scripts/deploy/*.sh
	$(DOCKER) run --rm \
		--volume "$(CURDIR)/infra/Caddyfile.production:/etc/caddy/Caddyfile:ro" \
		--entrypoint caddy \
		caddy:2.10.2-alpine@sha256:4c6e91c6ed0e2fa03efd5b44747b625fec79bc9cd06ac5235a779726618e530d \
		validate --config /etc/caddy/Caddyfile --adapter caddyfile

shared-edge-proof: ## Prove the inert shared Nginx/Certbot edge locally.
	python3 -m scripts.prove_shared_edge_topology
	python3 -m scripts.prove_shared_edge_runtime

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

import-dry-run: ## Preview exact new/changed rows and pending work without canonical writes.
	$(IMPORTER) dry-run

import-persist: ## Persist only new or changed source messages in bounded batches.
	$(IMPORTER) persist

import-geocode: ## Resume cache-first Geoapify work under durable rate/daily limits.
	$(IMPORTER) geocode

import-media: ## Resume safe original storage and public derivative generation.
	$(IMPORTER) media

import-verify: ## Reconcile aggregate source/canonical/geocode/media counts.
	$(IMPORTER) verify

import-run: ## Run persistence, geocoding, media, and verification until complete or paused.
	$(IMPORTER) run

seed-m1: ## Converge the invented local M1 fixture after migrations.
	$(COMPOSE) --profile operator run --rm seed
