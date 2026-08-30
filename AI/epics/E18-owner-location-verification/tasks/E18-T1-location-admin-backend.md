---
schema: ai-workflow/task@1
id: E18-T1
epic: E18
title: "Location admin backend service"
status: in_progress
revision: 1
priority: P1
size: M
milestone: M5
dependencies: []
requirement_ids:
  - P-008
decision_ids:
  - ADR-012
  - ADR-016
  - ADR-021
deferred_decision_ids: []
promotion:
  source: ../proposed-tasks/E18-T1-location-admin-backend.md
  promoted_by: "ZCode agent under owner instruction"
  promoted_at: "2026-08-30T11:03:58Z"
spike_gate:
  status: satisfied
  file: ../SPIKE.md
  approved_revision: 1
  verified_by: "ZCode agent under owner instruction"
  verified_at: "2026-08-30T11:03:58Z"
implementation_gate:
  status: satisfied
  file: ../IMPLEMENTATION_PLAN.md
  approved_revision: 1
  verified_by: "ZCode agent under owner instruction"
  verified_at: "2026-08-30T11:03:58Z"
dependency_gate:
  status: satisfied
  verified_by: "ZCode agent under owner instruction"
  verified_at: "2026-08-30T11:03:58Z"
  evidence: []
branch:
  required: true
  name: feat/E18-T1-location-admin-backend
  task_id: E18-T1
  one_task_only: true
  created_at: "2026-08-30T11:20:00Z"
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

# E18-T1: Location admin backend service

## Outcome

The owner console application layer can list and filter every canonical location
(pending queue by default), load one location's verification detail with its latest
offers and geocode candidate, and apply the operator decisions accept-candidate,
reject, unresolve, and manual set-point — each as one transactional lineage append
plus location update with an owner-attributed audit event.

## Scope

- Application layer (`features/admin/application/admin_ops.py`):
  `LocationAdminSummary`, `LocationEditDetail`, `OfferContextSummary`,
  `GeocodeCandidateSummary` frozen dataclasses; `LocationAdminReader` and
  `LocationDecisionStore` protocols; interactors `ListLocations` (status filter
  default `pending` = `needs_review`+`ungeocoded`, plus `accepted`, `rejected`,
  `ungeocoded`, `needs_review`, `all`; address substring search; limit),
  `GetLocationForEdit`, `AcceptPlaceCandidate`, `RejectPlace`, `UnresolvePlace`,
  `SetPlacePoint` (any from-state; `within_warsaw` validation;
  `precision=building`, `confidence=1.00`, `manual_accept`,
  `geocode_result_id=null`); `AdminService` extension.
- Infrastructure (`features/admin/infrastructure/place_store.py`):
  `SQLAlchemyLocationAdminStore` implementing both ports — latest-selection
  row-number join, candidate result join, latest offers per location, transactional
  transitions mirroring `SQLAlchemyAcceptPendingGeocodePinsAdapter`.
- Composition wiring of the new interactors into `AdminService`.
- Unit tests with in-memory fakes and PostGIS integration tests.

## Out of scope

- Any HTML/interface work, static assets, routes, or documentation updates
  (E18-T2).
- Schema migrations, public API endpoints, contract changes, frontend changes.
- Bulk operations, pagination, re-geocoding triggers, non-coordinate field edits.

## Affected modules and contracts

- `apps/backend/src/wef_backend/features/admin/application/admin_ops.py`
- `apps/backend/src/wef_backend/features/admin/infrastructure/place_store.py` (new)
- `apps/backend/src/wef_backend/features/admin/infrastructure/__init__.py`
- `apps/backend/src/wef_backend/composition.py`
- `apps/backend/tests/fakes.py`, `apps/backend/tests/test_admin_ops.py` (or
  sibling unit test module), new integration test module
- No database migration; no public contract change.

## Implementation notes

- Transitions follow the accepted lineage recipe: from/to states from
  `LocationReviewStatus`, `reason_code` from `SelectionReason`
  (`manual_accept`/`manual_reject`/`manual_unresolve`), `actor_type="operator"`,
  `actor_id=str(owner_id)`, `review_policy_version=REVIEW_POLICY_VERSION`,
  `selection_version = COALESCE(max, 0) + 1`.
- Accept-candidate requires the latest selection's geocode result to carry an
  in-scope non-null point; otherwise the interactor records a denied audit event
  and raises `AdminDeniedError`.
- Set-point and accept-candidate set `out_of_scope=false` so
  `ck_locations_accepted_public_point` holds; reject/unresolve never clear an
  existing point (public eligibility is driven by `review_status`).
- Denied outcomes (unknown location, missing candidate, out-of-scope point) record
  `AdminAuditEvent`s with `AdminOutcome.DENIED`, action names
  `accept_place`/`reject_place`/`unresolve_place`/`set_place_point`,
  `target_type="location"`.

## Acceptance criteria

- [ ] `ListLocations` returns summaries for every review status with working
  `pending` default filter, explicit status filters, address substring search,
  and a bounded limit, ordered newest-activity-first.
- [ ] `GetLocationForEdit` returns the location, its latest offers (excerpts,
  price/area/rooms, visibility, published), its latest decision reason, and any
  in-scope candidate point.
- [ ] Each decision interactor appends exactly one lineage row with the correct
  from/to state, reason, actor, policy version, and `selection_version+1`, updates
  `locations` accordingly, and records an allowed audit event.
- [ ] `SetPlacePoint` accepts coordinates for any from-state after `within_warsaw`
  validation and stores `precision=building`, `confidence=1.00`,
  `selected_geocode_result_id` unchanged, `out_of_scope=false`.
- [ ] Denied paths (unknown location, accept without in-scope candidate,
  out-of-scope manual point) change nothing, record denied audit events, and raise
  `AdminDeniedError`.
- [ ] Unit tests with fakes plus PostGIS integration tests pass locally under
  `make test-backend`.

## Test plan

- Unit: interactor allowed/denied paths with in-memory fakes (new fakes in
  `tests/fakes.py`, `build_admin_service` extension).
- Integration: `pytest.mark.integration` module seeding locations, selections, and
  geocode results against the containerized PostGIS test database; asserts
  filters, ordering, and post-transition state including lineage rows.
- Contract/migration: none required (no contract or schema change); `make
  contract-check` must stay green.
- End-to-end: console flows covered in E18-T2.
- Security/operations: denied-path audit evidence in unit/integration tests.

## Rollout and rollback

- No migration; ship with the standard pipeline after green CI. Rollback is a
  plain revert + redeploy; appended lineage rows are append-only history.

## Ready checklist

- [x] The file is authoritative under `tasks/`; no duplicate remains under
  `proposed-tasks/`.
- [x] Promotion source, promoter, and timestamp are recorded.
- [x] `spike_gate` references the owner-approved current spike revision and is
  `satisfied`.
- [x] `implementation_gate` references the owner-approved current
  implementation-plan revision, which contains this task ID/current revision, and
  is `satisfied`.
- [x] Every dependency is `done` with `dependency_gate: satisfied` (no
  dependencies); every deferred gate is resolved.
- [x] Scope and acceptance criteria match the approved plan.

## Start checklist

- [x] Status passed through `ready`.
- [x] One new branch contains this task ID.
- [x] The branch and pull request contain this task only.
- [x] `branch.name` and `branch.created_at` are recorded before setting
  `in_progress`.

## Done checklist

- [ ] Acceptance criteria pass.
- [ ] The global [definition of done](../../../workflow/DEFINITION_OF_DONE.md) passes.
- [ ] Completion actor, time, pull request, and evidence are recorded.
