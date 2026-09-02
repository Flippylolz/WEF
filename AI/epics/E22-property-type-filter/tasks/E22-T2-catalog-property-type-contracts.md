---
schema: ai-workflow/task@1
id: E22-T2
epic: E22
title: "Extend catalog filter and public contracts"
status: done
revision: 1
priority: P1
size: M
milestone: M5
dependencies: [E4-T4, E22-T1]
requirement_ids: [P-001, P-002, P-003, P-010]
decision_ids: [ADR-005, ADR-012, ADR-013]
deferred_decision_ids: []
promotion:
  source: ../proposed-tasks/E22-T2-catalog-property-type-contracts.md
  promoted_by: "Codex agent (owner-approved E22 spike revision 1)"
  promoted_at: "2026-09-02T15:46:31Z"
spike_gate:
  status: satisfied
  file: ../SPIKE.md
  approved_revision: 1
  verified_by: "Codex agent"
  verified_at: "2026-09-02T15:46:31Z"
implementation_gate:
  status: satisfied
  file: ../IMPLEMENTATION_PLAN.md
  approved_revision: 2
  verified_by: "Codex agent"
  verified_at: "2026-09-02T15:58:32Z"
dependency_gate:
  status: satisfied
  verified_by: "Codex agent"
  verified_at: "2026-09-02T17:27:00Z"
  evidence:
    - "E22-T1 done through https://github.com/Flippylolz/WEF/pull/302"
    - "E4-T4 done on main before E22 implementation"
branch:
  required: true
  name: null
  task_id: E22-T2
  one_task_only: true
  created_at: null
  pull_request: https://github.com/Flippylolz/WEF/pull/302
completion:
  completed_by: "Codex agent"
  completed_at: "2026-09-02T17:27:00Z"
  pull_request: https://github.com/Flippylolz/WEF/pull/302
  evidence:
    - "OpenAPI and generated api.ts updated in PR #302"
    - "Production facets smoke in PRODUCTION_EVIDENCE.md"
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# E22-T2: Extend catalog filter and public contracts

## Outcome

All public catalog query paths accept the same property-type filter and expose
canonical property-type facets and offer values through committed OpenAPI
contracts.

## Scope

- Add repeated `property_type` request values from the three classified choices to
  `MapFilters` and the shared HTTP query model; keep `unknown` response-only.
- Include property types in normalized filter/cache identity and quick-filter copy
  paths without changing quick-filter meaning.
- Add the SQL predicate once and reuse it for grouped map, viewport listings, and
  selected-location matching/counts.
- Add classified property types to canonical facets; exclude `unknown` from the
  selectable facet list.
- Add `property_type` to offer summaries and detail projections, including
  `unknown` for incomplete records.
- Update contract docs, committed OpenAPI, generated TypeScript, tests, and
  evidence-based query indexes.

## Out of scope

- Source classification/backfill and public frontend controls.
- New endpoints or client-owned filtering.
- Making unknown a selectable filter option.
- Changing any existing parameter or response meaning.

## Affected modules and contracts

- Catalog application `MapFilters`, facet/browse/detail DTOs and ports.
- Catalog interface query models/presenters and shared SQLAlchemy query adapters.
- Offer/filter index selection supported by representative query-plan evidence.
- `AI/contracts/HTTP_API.md`, `AI/contracts/DATA_MODEL.md`, committed OpenAPI, and
  generated frontend API types.
- Backend unit, Postgres/PostGIS integration, API, contract, and performance tests.

## Implementation notes

- Use a three-value filter input type and the four-value stored/response
  `PropertyType`; `unknown` must return 422 as filter input.
- Add the property predicate to the existing shared filter-condition builder so
  grouped pins, location matching, and viewport results cannot diverge.
- Keep facet ordering product-defined rather than alphabetical if the database
  returns a different order.
- Add or extend an index only after representative `EXPLAIN` evidence.

## Work

- Preserve OR-within-property-type and AND-across-filter-group behavior.
- Ensure no active property filter means no property predicate, so unknown rows
  remain in ordinary browsing.
- Ensure active filters exclude unknown rows and invalid enum values return 422.
- Capture representative query plans before deciding whether to extend/add an
  offer filter index.

## Acceptance criteria

- [ ] The map, viewport list, and selected-location results agree for each type and
  every supported multi-selection.
- [ ] Property types OR together; property type ANDs with price, area, rooms,
  district, market, content, publication, quick filter, and bounding box.
- [ ] Unknown offers appear with no active property filter and never match an
  active classified selection.
- [ ] A manual `property_type=unknown` or unsupported value returns 422 rather than
  creating an undocumented filter mode.
- [ ] Facets expose only classified values present in visible, accepted, in-scope
  catalog data and use stable ordering.
- [ ] Offer summary/detail responses expose the canonical value, including
  `unknown`, without exposing source evidence.
- [ ] Equivalent repeated-value orderings produce the same normalized cache key;
  changing the selection changes it.
- [ ] OpenAPI and generated types are current and compatibility checks pass.
- [ ] Query-plan evidence demonstrates the established performance budget and
  justifies any added index.

## Dependencies and gates

- E4-T4 is done and supplies the hardened shared catalog query path.
- E22-T1 must be done or represented by a valid direct ancestor stack before work;
  it must be done before E22-T2 completes.
- Requires the E22 approval, promotion, dependency, and dedicated-branch gates.

## Risks and notes

Adding the enum in some projections but not others would create misleading pin
counts and selected-location results. Integration tests must treat agreement across
all three query paths as the central acceptance boundary.

## Test plan

- Unit: input validation, normalized filter identity, facet ordering, presenter
  values, and quick-filter copying.
- Integration: OR-within/AND-across matrices, unknown behavior, map/list/location
  agreement, selected-location ranks/counts, and offer detail.
- Contract/migration: OpenAPI generation/compatibility and generated TypeScript;
  no migration in this task.
- End-to-end: API-level deep-link parameters; browser UI belongs to E22-T3.
- Security/operations: invalid-value 422, bounded repeated values, query-plan and
  timing evidence without logging filter source data.

## Rollout and rollback

Deploy only after E22-T1's compatible schema is live. The API change is additive;
old clients and URLs remain valid. Rollback uses the prior application image and
requires no data rollback because the property column remains unused but compatible.

## Ready checklist

- [x] The file is authoritative under `tasks/`; no duplicate remains under
  `proposed-tasks/`.
- [x] Promotion source, promoter, and timestamp are recorded.
- [x] `spike_gate` references approved E22 spike revision 1.
- [x] `implementation_gate` references an approved plan containing this task and
  revision.
- [ ] E4-T4 and E22-T1 have satisfied dependency evidence before `ready`.
- [x] Scope and acceptance criteria match approved spike revision 1.
