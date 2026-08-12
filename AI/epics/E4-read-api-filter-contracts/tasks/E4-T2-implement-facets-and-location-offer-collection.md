---
schema: ai-workflow/task@1
id: E4-T2
epic: E4
title: "Implement facets and location offer collection"
status: draft
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
  status: blocked
  verified_by: null
  verified_at: null
  evidence: []
branch:
  required: true
  name: null
  task_id: E4-T2
  one_task_only: true
  created_at: null
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
- Cursor order is `published_at DESC, id DESC` and cursor payload is opaque/versioned.
- Map and collection invoke the same normalized filter object and range/null semantics.
- Unknown UUIDs return a safe not-found response without leaking hidden records.

## Acceptance criteria

- [ ] Facet values are canonical, stable, generated from visible/in-scope M1 data, and contract-tested.
- [ ] Selected-location summaries return matching offers first with published date and backend display/confidence values.
- [ ] Cursor pagination has no duplicate/omitted rows under timestamp ties and rejects invalid cursors safely.
- [ ] `include_non_matching` is explicit and matching/total counts remain accurate.
- [ ] Map, facet, and collection endpoints share tested filter semantics.
- [ ] OpenAPI/generated-client/docs/compatibility and sensitive-field allowlist checks pass.

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
- [ ] E4-T1 is `done` or a direct ancestor PR recorded as `stacked`.
- [x] Scope and acceptance match the approved plan.

## Start checklist

- [ ] Status passes through `ready`.
- [ ] Dedicated E4-T2 branch is created and recorded.
- [ ] Branch/PR contain E4-T2 only.

## Done checklist

- [ ] Acceptance criteria pass.
- [ ] The global [definition of done](../../../workflow/DEFINITION_OF_DONE.md) passes.
- [ ] Completion actor, time, pull request, and evidence are recorded.
