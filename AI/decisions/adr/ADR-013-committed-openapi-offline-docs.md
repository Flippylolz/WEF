---
schema: ai-docs/adr@1
id: ADR-013
title: Commit OpenAPI and keep production docs offline
status: accepted
date: 2026-08-12
supersedes: []
superseded_by: []
resolves: []
---

# ADR-013: Commit OpenAPI and keep production docs offline

- Status: accepted
- Date: 2026-08-12
- Decision: generate deterministic OpenAPI from FastAPI into committed `contracts/openapi/v1.json`; generate frontend TypeScript with `openapi-typescript`/`openapi-fetch`, and publish JSON/types/static Redocly HTML as commit-addressed CI artifacts.
- Rationale: the frontend needs an offline, reviewable, versioned contract that does not depend on a running backend, while production should expose no unnecessary schema/documentation routes.
- Consequence: production sets `openapi_url=None`, `docs_url=None`, and `redoc_url=None`; runtime images contain no docs tooling/assets. CI fails on stale schemas, unintended breaking changes, lint failures, or generated frontend type mismatches.
- Detailed contract: [OpenAPI contract and frontend generation](../../contracts/OPENAPI.md).
