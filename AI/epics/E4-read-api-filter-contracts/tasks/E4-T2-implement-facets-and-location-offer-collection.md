---
schema: ai-workflow/task@1
id: E4-T2
epic: E4
title: "Implement facets and location offer collection"
status: in_progress
revision: 2
priority: P0
size: M
milestone: M1
dependencies: [E4-T1]
requirement_ids: [P-001, P-002, P-003]
decision_ids: [ADR-002, ADR-003, ADR-012, ADR-013]
deferred_decision_ids: []
promotion:
  source: ../proposed-tasks/E4-T2-implement-facets-and-location-offer-collection.md
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
  status: stacked
  verified_by: "Cursor Agent"
  verified_at: "2026-08-12T23:12:03Z"
  evidence:
    - "E4-T1 dependency | branch feature/E4-T1-map-geojson | PR https://github.com/Flippylolz/WEF/pull/12 | head d32ee31"
branch:
  required: true
  name: feature/E4-T2-facets-results
  task_id: E4-T2
  one_task_only: true
  created_at: "2026-08-12T23:12:03Z"
  pull_request: null
completion:
  completed_by: null
  completed_at: null
  pull_request: null
  evidence: []
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# E4-T2: Implement facets and location offer collection

## Outcome

Expose canonical M1 filter options and deterministic dated offers for a selected location using the exact map-query filter semantics.

## Scope

- Add `GET /api/v1/filter-facets` with canonical districts, rooms, market/content types, and dataset price/area/publication bounds.
- Add `GET /api/v1/locations/{location_id}/offers` with the shared filters, deterministic opaque cursor pagination, and explicit matching/total context.
- Return dated offer summaries with backend-owned display/confidence fields needed by the M1 result panel.
- Support deliberate `include_non_matching=true` without mixing matches/history silently.
- Extend OpenAPI/generated client and contract/integration tests.

## Out of scope

- Full offer detail, media/gallery, source text/link, contacts, auth, admin, free-text search, and complex search-engine aggregations.

## Affected modules and contracts

- Shared map filter/query application policy, new facet/collection query ports/adapters/presenters/routes, OpenAPI/types.
- [HTTP API](../../../contracts/HTTP_API.md).

## Implementation notes

- Facet values and range bounds come from backend data/contracts; frontend does not derive domain options from visible pins.
- Cursor order is `matches_filters DESC, published_at DESC, id DESC` so matching offers lead explicit history; the cursor payload is opaque/versioned.
- Map and collection invoke the same normalized filter object and range/null semantics.
- Unknown UUIDs return a safe not-found response without leaking hidden records.

## Acceptance criteria

- [x] Facet values are canonical, stable, generated from visible/in-scope M1 data, and contract-tested.
- [x] Selected-location summaries return matching offers first with published date and backend display/confidence values.
- [x] Cursor pagination has no duplicate/omitted rows under timestamp ties and rejects invalid cursors safely.
- [x] `include_non_matching` is explicit and matching/total counts remain accurate.
- [x] Map, facet, and collection endpoints share tested filter semantics.
- [x] OpenAPI/generated-client/docs/compatibility and sensitive-field allowlist checks pass.

## Test plan

- Unit: cursor codec and presenters.
- Integration: facet aggregation, matching/history split, pagination tie cases, hidden/out-of-scope behavior.
- Contract: OpenAPI/generated client and response shapes.
- End-to-end: click-location API flow through Caddy against M1 seed.
- Security: invalid/hidden IDs and cursor/query abuse return safe responses.

## Rollout and rollback

Additive endpoints over the E3 schema and E4-T1 policy. Roll back only the application to a compatible release; this task adds no migration or destructive data operation.

## Ready checklist

- [x] This file is authoritative under `tasks/`; the proposed source is removed.
- [x] Promotion, spike revision 2, and plan revision 2 are recorded.
- [x] E4-T1 is a direct ancestor PR recorded as `stacked`.
- [x] Scope and acceptance match the approved plan.

## Start checklist

- [x] Status passed through `ready`.
- [x] Dedicated `feature/E4-T2-facets-results` branch is created and recorded.
- [x] Branch contains E4-T2 only; its PR opens after verification.

## Done checklist

- [x] Acceptance criteria pass.
- [ ] The global [definition of done](../../../workflow/DEFINITION_OF_DONE.md) passes.
- [ ] Completion actor, time, pull request, and evidence are recorded.

## Verification evidence

- Static/unit: Ruff, six import-linter contracts, mypy strict, 43 backend tests passed/4 explicit integration skips at 90.06% coverage, and frontend lint/type/tests pass.
- PostGIS: three integration tests pass for map filters, canonical visible facets, explicit match/history counts, matches-first ordering, opaque pagination across timestamp ties, migrations, and seed replay.
- Contract: deterministic OpenAPI/TypeScript generation, Redocly lint/static docs, deliberate drift rejection, and oasdiff against E4-T1 report no breaking changes.
- Runtime: Caddy-served facets return four canonical districts; a center-location primary filter pages one matching then one non-matching offer without duplicates, and an unknown public UUID returns the bounded 404 envelope.
- Safety: offer summaries contain only structured allowlisted fields; source text/link, media, contacts, payloads, local paths, and provider data remain absent.
