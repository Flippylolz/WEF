---
schema: ai-workflow/implementation-plan@1
epic: E18
title: "Owner location management and verification delivery"
status: approved
revision: 1
owner: owner
spike_revision: 1
task_sequence:
  - id: E18-T1
    revision: 1
  - id: E18-T2
    revision: 1
approval:
  required_role: owner
  status: approved
  decided_by: "owner"
  decided_at: "2026-08-30T11:03:58Z"
  approved_revision: 1
  evidence: "ZCode session owner instruction on 2026-08-30: implement this epic; PR merges are allowed after the CI is green; deployment health must be verified after merges"
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# Implementation Plan: Owner location management and verification delivery

## Approved spike baseline

- [E18 spike revision 1](SPIKE.md) was owner-approved on 2026-08-30.
- The binding recommendations are: one filterable owner console page over all
  locations (pending queue by default); a full-page set-point picker showing the
  offer data beside a dependency-free slippy map; every decision appended to the
  existing `location_geocode_selections` lineage with operator attribution and an
  admin audit event; manual points validated against the Warsaw scope with
  `precision=building`, `confidence=1.00`; no schema and no public-contract
  changes.

## Scope and outcome

Deliver two independently reviewable changes so that the owner can (1) browse and
filter every canonical location from `/admin/places`, (2) inspect the retained
offer evidence behind each address, (3) place or correct a location's map point by
hand for any location, including accepted ones, (4) accept an in-scope candidate
point, reject a location, or send a decided location back to review, and (5) rely
on every action being lineage-tracked and audit-logged. Explicit exclusions:
editing non-coordinate location fields (display name, district, normalized
address), bulk operations, pagination beyond the existing 100-row admin view cap,
re-geocoding triggers from the console, and any public API or frontend change.

## Ordered task sequence

1. [E18-T1](tasks/E18-T1-location-admin-backend.md) — the backend service slice:
   ports, interactors, SQLAlchemy store, composition wiring, unit and PostGIS
   integration tests. Independently reviewable as pure application/infrastructure
   behavior with no HTML; E18-T2 consumes its interactors.
2. [E18-T2](tasks/E18-T2-location-admin-console.md) — depends on E18-T1 (`done`):
   the console slice — filterable list view, full-page picker with static slippy-map
   script, action routes, admin HTTP tests, and the affected `AI/` documentation.
   Independently reviewable as the only user-facing surface of the epic.

## Cross-task architecture

- Dependency direction stays inward: `admin.interface` → `admin.application`
  (interactors + protocols) → domain values imported from catalog/ingestion;
  `admin.infrastructure` implements the admin application ports and may import
  catalog/ingestion infrastructure models (existing precedent: the admin audit
  store importing `contacts.infrastructure.models`).
- Transaction boundary: one decision = one store transaction appending exactly one
  lineage row and updating one `locations` row; audit events are recorded by the
  interactors through the existing `AdminAuditStore`.
- No generated contracts are touched; the admin console remains outside OpenAPI.
- Domain/application rules (review states, scope validation, lineage versioning)
  live only in the admin application layer and shared domain modules; the interface
  layer renders HTML only.

## Data and migrations

- No Alembic migration. `location_geocode_selections.geocode_result_id` is already
  nullable; `ck_locations_accepted_public_point` is preserved because manual
  accepts require an in-scope validated point and `out_of_scope=false`.
- Lineage `selection_version` continues monotonically per location
  (`COALESCE(max, 0) + 1`) so console decisions interleave safely with the
  recurring geocoder and the batch-accept CLI.
- Rollback of the code reverts behavior only; appended lineage rows are historical
  facts and are never rewritten.

## Security and privacy

- Every route sits under the existing `/admin` mount behind `OwnerAuthProvider`
  (owner session) and `AdminMutationGuardMiddleware` (same-origin + mutation rate
  limit); forms carry `csrf_input`.
- Offer text shown to the owner is the already-retained `source_text_excerpt`
  (masked public text is not needed for owner triage); no contact data is
  displayed.
- Negative tests: non-owner gets the login flow, missing/foreign CSRF or origin is
  rejected, unknown location ids are denied, out-of-scope coordinates are refused
  with an error banner, and denied attempts leave `allowed=false` audit rows.

## Test and verification strategy

- Unit (E18-T1): interactors with in-memory fakes — allowed/denied paths, audit
  outcomes, scope validation, unknown ids.
- Integration (E18-T1): real PostGIS via the containerized test database — filters,
  search, ordering, and each transition's resulting `locations` state plus appended
  lineage row (`selection_version+1`, from/to states, reason, actor).
- HTTP (E18-T2): the real app with fake services — list rendering per filter and
  search, picker page content (offer data, form, script tag), all POST routes
  (happy, invalid, denied), CSRF/origin enforcement, owner gating.
- Static analysis per repository rules: `make lint`, `make format-check`,
  `make typecheck`; `make contract-check` is unaffected (no contract change).
- Manual verification after each merge: production deploy workflow green, health
  endpoint OK, `/admin` serves, and the new page + picker work against production
  behind owner login.

## Operations, rollout, and rollback

- Release order follows the standard pipeline: merge on green CI → production
  deploy workflow → health verification. No configuration or environment change is
  required; the static picker script ships inside the backend image.
- Rollback: revert the merge and redeploy the previous release per
  `AI/operations/DEPLOYMENT.md`; no data rollback exists or is needed (lineage rows
  are append-only history). Backups remain deferred (ADR-015) and are unaffected.

## Risks and mitigations

- Bespoke slippy-map JS bugs → minimal interaction surface, lat/lng inputs as the
  authoritative entry, manual browser verification of the picker after E18-T2's
  merge (owning task: E18-T2).
- Owner actions racing the recurring geocoder → monotonic per-location
  `selection_version` and transactional updates (E18-T1).
- Oversized result sets → 100-row cap with search/filter-first navigation,
  consistent with all existing admin views (E18-T2).

## Invalidation triggers

- Schema or review-policy changes that move decision state off the lineage table.
- Owner requests for non-coordinate field editing, bulk tooling, or a different
  admin surface (per spike invalidation triggers).

## Approval checklist

- [x] The referenced spike revision has explicit owner approval and remains valid.
- [x] Every sequence entry is a promoted task with complete acceptance criteria
  and traceability.
- [x] Dependencies are complete, acyclic, and enforceable task by task.
- [x] Affected modules, contracts, tests, migrations, risks, rollout, and rollback
  are explicit.
- [x] Deferred decisions required for implementation are resolved.
- [x] No production or disposable proof code has been written.
- [x] `revision` represents the material plan being submitted.
- [x] `status` is `awaiting_approval` and approval remains `pending`.

## Owner decision

The owner recorded the decision in the YAML `approval` object on 2026-08-30
(ZCode session owner instruction; see `evidence`). Approval authorizes this plan
revision; each task still satisfies promotion, dependency, state, and
one-branch-per-task gates.
