---
schema: ai-workflow/task@1
id: E3-T1
epic: E3
title: "Create M1 schema, migrations, and deterministic seed"
status: in_progress
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
  name: feature/E3-T1-m1-schema-seed
  task_id: E3-T1
  one_task_only: true
  created_at: "2026-08-12T22:44:16Z"
  pull_request: "https://github.com/Flippylolz/WEF/pull/11"
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
- Keep the disposable E0 route/mapping isolated and unmigrated until E4-T1 replaces its public contract, then remove it in E4-T1.

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

- [x] Alembic upgrades an empty PostGIS database to head and a second upgrade is a no-op.
- [x] Location coordinates use `geometry(Point,4326)` with a GiST index and longitude/latitude order is integration-tested.
- [x] Offer visibility/publication/range constraints and query indexes exist; no real-world availability boolean exists.
- [x] The explicit synthetic seed converges to the same IDs/rows on replay without production/source data.
- [x] Local Compose starts through a migration gate and runs the seed only through an explicit operator command.
- [x] Readiness returns 503 when the database migration revision is incompatible.
- [x] The disposable proof table is absent from Alembic metadata/migrations; E4-T1 retires runtime access and deprecates its route under AD-012.

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
- [x] Dedicated `feature/E3-T1-m1-schema-seed` branch is created and recorded.
- [x] Branch contains E3-T1 only; its PR opens after verification.

## Done checklist

- [x] Acceptance criteria pass.
- [ ] The global [definition of done](../../../workflow/DEFINITION_OF_DONE.md) passes.
- [ ] Completion actor, time, pull request, and evidence are recorded.

## Verification evidence

- Static/unit: Ruff, import-linter (five contracts), mypy strict, 28 backend tests passed/2 explicit integration skips with 96.28% coverage, frontend checks, OpenAPI contract/docs, Markdown links, and Compose config pass.
- Migration integration: disposable PostGIS upgrade/re-upgrade, revision head, 13 named check constraints, GiST index, forbidden availability-column check, point order, prior proof-table isolation, and readiness pass.
- Runtime: local Compose built production images, applied migration before API, reached healthy/ready through Caddy, and rejected a deliberately mismatched revision.
- Seed: two explicit runs converged to four locations/five offers; production environment exited non-zero before persistence; no source/provider/media/contact data was used.
- Rollback boundary: no automatic downgrade/reset/destructive volume target exists.
