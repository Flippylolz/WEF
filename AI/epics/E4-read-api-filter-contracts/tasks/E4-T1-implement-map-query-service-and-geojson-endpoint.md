---
schema: ai-workflow/task@1
id: E4-T1
epic: E4
title: "Implement map query service and GeoJSON endpoint"
status: done
revision: 2
priority: P0
size: L
milestone: M1
dependencies: [E3-T1]
requirement_ids: [P-001, P-003]
decision_ids: [ADR-002, ADR-003, ADR-005, ADR-012, ADR-013]
deferred_decision_ids: []
promotion:
  source: ../proposed-tasks/E4-T1-implement-map-query-service-and-geojson-endpoint.md
  promoted_by: "Cursor Agent (owner-authorized)"
  promoted_at: "2026-08-12T22:34:40Z"
spike_gate:
  status: satisfied
  file: ../SPIKE.md
  approved_revision: 2
  verified_by: "Cursor Agent"
  verified_at: "2026-08-12T22:34:40Z"
implementation_gate:
  status: satisfied
  file: ../IMPLEMENTATION_PLAN.md
  approved_revision: 2
  verified_by: "Cursor Agent"
  verified_at: "2026-08-12T22:34:40Z"
dependency_gate:
  status: satisfied
  verified_by: "Cursor Agent (owner-authorized reconciliation)"
  verified_at: "2026-08-13T17:44:22Z"
  evidence:
    - "E3-T1 | done | merged PR https://github.com/Flippylolz/WEF/pull/11 | integrated stack f766a63"
branch:
  required: true
  name: feature/E4-T1-map-geojson
  task_id: E4-T1
  one_task_only: true
  created_at: "2026-08-12T22:56:40Z"
  pull_request: "https://github.com/Flippylolz/WEF/pull/12"
completion:
  completed_by: "Flippylolz (owner-authorized reconciliation)"
  completed_at: "2026-08-13T14:52:45Z"
  pull_request: "https://github.com/Flippylolz/WEF/pull/12"
  evidence:
    - "Task PR merged into the ordered stack at f766a63517b6ba49a1377e630ea54e9cb4e0e56f"
    - "Integrated main CI passed for ad4d6de: https://github.com/Flippylolz/WEF/actions/runs/31726996540"
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# E4-T1: Implement map query service and GeoJSON endpoint

## Outcome

Expose one backend-authoritative grouped Warsaw map query with complete M1 filter semantics through deterministic GeoJSON and generated OpenAPI types.

## Scope

- Add immutable application filter/query DTOs and validation for bbox, price, area, rooms, districts, market/content types, and publication range.
- Add a query-service port and SQLAlchemy/PostGIS adapter that filters visible offers and groups accepted in-scope locations.
- Return matching/total counts, display metadata, coordinate precision/confidence, latest matching publication timestamp, and comparable price/area summaries.
- Add a pure Pydantic GeoJSON presenter and `GET /api/v1/map/locations`.
- Add normalized filter/data-version ETag and conditional `304`.
- Retire E0 proof persistence after the map contract passes; keep `/estates` inert/deprecated until its frontend consumer is removed.

## Out of scope

- Facets, location/offer collections, details, media, source text/links, auth, contacts, real geocoding, and frontend rendering.

## Affected modules and contracts

- New map/catalog application/domain/interface/infrastructure modules, composition root, FastAPI routes, OpenAPI contract, generated frontend types, and integration/contract tests.
- [HTTP API](../../../contracts/HTTP_API.md) and [OpenAPI](../../../contracts/OPENAPI.md).

## Implementation notes

- Different filter groups use AND; repeated values within a group use OR.
- Stored ranges intersect requested ranges inclusively; null does not match an active filter.
- Only `visibility=visible`, `review_status=accepted`, in-scope, non-null points appear.
- Coordinates serialize as `[longitude, latitude]`; no ORM entity leaves infrastructure.
- Route invokes one query service and presenter; business/filter logic does not enter FastAPI or frontend code.
- Real records cannot rely on the synthetic-fixture exception; accepted geocoding remains a later gate.

## Acceptance criteria

- [x] Required Warsaw-safe bbox and every M1 filter are validated; unknown/malformed/unsafe queries return stable safe errors.
- [x] Grouped GeoJSON matches the documented contract and includes only locations with at least one matching visible offer.
- [x] Inclusive range, null, AND/OR, date, visibility, scope, review-state, and coordinate-order behavior have PostGIS integration tests.
- [x] Matching and total counts differ correctly when filters exclude related offers.
- [x] ETag is deterministic for normalized equivalent filters and `If-None-Match` returns `304`.
- [x] OpenAPI, generated TypeScript, lint/docs, and compatibility checks pass.
- [x] Representative synthetic query is within the 500 ms local integration budget and its plan is inspectable.
- [x] No raw payload, contact, path, provider response, full source text, or unverified link enters the response.

## Test plan

- Unit: filter value validation/normalization and presenter serialization.
- Integration: real PostGIS grouped/filter queries and indexes.
- Contract: OpenAPI/generation/compatibility plus response snapshots.
- End-to-end: seeded M1 endpoint through local Caddy.
- Security/performance: oversized bbox/query rejection, no sensitive fields, representative timing/query plan.

## Rollout and rollback

Deploy only after E3-T1 migration/seed compatibility. The map endpoint is additive; the proof route remains inert/deprecated under AD-012 until its consumer is removed. Roll back the application only to a schema-compatible release; no data migration or destructive rollback is introduced here.

## Ready checklist

- [x] This file is authoritative under `tasks/`; the proposed source is removed.
- [x] Promotion, spike revision 2, and plan revision 2 are recorded.
- [x] E3-T1 completion is recorded by the satisfied dependency gate.
- [x] Scope and acceptance match the approved plan.

## Start checklist

- [x] Status passed through `ready`.
- [x] Dedicated `feature/E4-T1-map-geojson` branch is created and recorded.
- [x] Branch contains E4-T1 only; its PR opens after verification.

## Done checklist

- [x] Acceptance criteria pass.
- [x] The global [definition of done](../../../workflow/DEFINITION_OF_DONE.md) passes.
- [x] Completion actor, time, pull request, and evidence are recorded.

## Verification evidence

- Static/unit: Ruff, six import-linter contracts, mypy strict, 38 backend tests passed/3 explicit integration skips at 90.17% coverage, and frontend lint/type/tests pass.
- PostGIS: migration plus grouped-query integrations pass against the Compose database, covering all M1 filters, inclusive/null semantics, AND/OR groups, gating, point order, count differences, and a warmed query under 500 ms with `EXPLAIN`.
- Contract: deterministic OpenAPI, generated TypeScript, Redocly lint/static HTML, drift negative probe, and oasdiff against the stacked base pass.
- Runtime: production API image and migration gate are healthy through Caddy; the seed returns four features/five matches, conditional ETag returns 304, and the deprecated E0 route returns an inert empty response without obsolete table access.
- Safety: strict unknown-query rejection uses bounded problem JSON; response schema contains no source payload, contacts, local paths, provider data, full text, or links.
