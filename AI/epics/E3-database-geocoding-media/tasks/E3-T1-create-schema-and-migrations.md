---
schema: ai-workflow/task@1
id: E3-T1
epic: E3
title: "Create M1 schema, migrations, and deterministic seed"
status: ready
revision: 2
priority: P0
size: L
milestone: M1
dependencies: [E1-T3]
requirement_ids: [P-001, P-002, P-007]
decision_ids: [ADR-003, ADR-005, ADR-012]
deferred_decision_ids: []
promotion:
  source: ../proposed-tasks/E3-T1-create-schema-and-migrations.md
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
  verified_at: "2026-08-12T22:34:40Z"
  evidence:
    - "E1-T3 dependency | branch feature/E1-T3-local-compose | PR https://github.com/Flippylolz/WEF/pull/9 | head 1fbc639"
branch:
  required: true
  name: null
  task_id: E3-T1
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

# E3-T1: Create M1 schema, migrations, and deterministic seed

## Outcome

Replace disposable proof persistence with a forward-migrated M1 `Location`/`Offer` model and an explicit idempotent synthetic seed that can drive map/API/UI verification.

## Scope

- Add an async-compatible Alembic environment and initial PostgreSQL/PostGIS migration.
- Model canonical locations and dated offers with UUID public IDs, accepted/reviewed coordinates, visibility, market/content types, price/area ranges, room ranges, publication timestamps, and required timestamps.
- Add source uniqueness only where needed by the deterministic seed; historical lineage tables remain E3-T2 scope.
- Add GiST/B-tree indexes required by the first grouped-map query.
- Add an explicit backend command that upserts a small, clearly synthetic Warsaw fixture with fixed accepted coordinates.
- Update local Compose to run migrations as a one-shot health gate and expose seed as an operator-profile command.
- Remove the disposable `e0_proof_estates` mapping after replacement tests pass.

## Out of scope

- Real export parsing/persistence, source revisions/checkpoints, provider geocoding, media, contacts, authentication, full dataset import, and automatic production seeding.

## Affected modules and contracts

- `apps/backend/alembic.ini`, `apps/backend/migrations/**`, persistence mappings, composition/readiness, backend operator commands, and `infra/compose.yaml`.
- Persisted semantics remain governed by [Data model](../../../contracts/DATA_MODEL.md); this task implements the M1 subset only.

## Implementation notes

- No field named `available`, `active`, or `sold` may be introduced.
- Coordinates are nullable generally; only fixed synthetic fixtures are accepted without a geocoder record.
- Range bounds remain nullable and use integer minor units/numeric square metres.
- The seed command is deterministic/idempotent and refuses production environment.
- Migration upgrade is forward-only; no automatic schema downgrade is part of rollback.

## Acceptance criteria

- [ ] Alembic upgrades an empty PostGIS database to head and a second upgrade is a no-op.
- [ ] Location coordinates use `geometry(Point,4326)` with a GiST index and GeoJSON longitude/latitude order is testable.
- [ ] Offer visibility/publication/range constraints and query indexes exist; no real-world availability boolean exists.
- [ ] The explicit synthetic seed converges to the same IDs/rows on replay without production/source data.
- [ ] Local Compose starts through a migration gate and can run the seed only through an explicit operator command.
- [ ] Readiness fails when the database migration revision is incompatible.
- [ ] The disposable proof table/model is removed without leaving competing persistence.

## Test plan

- Unit: seed environment guard, deterministic IDs, range/enum validation.
- Integration: clean migration, repeated migration, seed replay, PostGIS coordinate/index checks.
- Contract/migration: previous E0 database upgrade path and Alembic head compatibility.
- End-to-end: migrated/seeded local Compose API readiness.
- Security/operations: no private source fields, contacts, credentials, provider calls, or automatic production seed.

## Rollout and rollback

Apply the forward migration before starting the new API. Before merge, discard only the task branch/local WEF database. After production use, roll application images back only when schema compatible; never auto-downgrade or claim data recovery while backups are deferred.

## Ready checklist

- [x] This file is authoritative under `tasks/`; the proposed source is removed.
- [x] Promotion source, promoter, and timestamp are recorded.
- [x] Spike revision 2 and implementation-plan revision 2 are approved and satisfied.
- [x] E1-T3 is a recorded direct ancestor PR under ADR-018.
- [x] Scope and acceptance criteria match the approved M1 plan.

## Start checklist

- [x] Status passed through `draft` to `ready`.
- [ ] Dedicated E3-T1 branch is created and recorded.
- [ ] Branch/PR contain E3-T1 only.

## Done checklist

- [ ] Acceptance criteria pass.
- [ ] The global [definition of done](../../../workflow/DEFINITION_OF_DONE.md) passes.
- [ ] Completion actor, time, pull request, and evidence are recorded.
