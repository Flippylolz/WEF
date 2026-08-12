---
schema: ai-workflow/implementation-plan@1
epic: E3
title: "M1 schema, migration, and deterministic seed plan"
status: approved
revision: 2
owner: owner
spike_revision: 2
task_sequence:
  - id: E3-T1
    revision: 2
approval:
  required_role: owner
  status: approved
  decided_by: Flippylolz
  decided_at: "2026-08-12T22:34:40Z"
  approved_revision: 2
  evidence: "Owner directive to prepare the MVP/autodeploy, choose safe defaults, log decisions/blockers, and continue stacking PRs"
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# Implementation Plan: M1 schema, migration, and deterministic seed

## Approved spike baseline

[E3 spike revision 2](SPIKE.md) approves only the persisted M1 map boundary. It keeps historical source/revision persistence, provider geocoding, media, contacts, and full import proposed.

## Scope and outcome

Deliver a clean-install/upgradeable PostGIS schema for canonical locations and dated offers plus an explicit idempotent synthetic seed. This replaces the disposable E0 table and makes downstream grouped-map/API/UI tasks independently testable without real source data or network calls.

## Ordered task sequence

### 1. E3-T1 — Create M1 schema, migrations, and deterministic seed

- Task: [E3-T1 revision 2](tasks/E3-T1-create-schema-and-migrations.md).
- Dependency: E1-T3 is the direct ancestor [PR #9](https://github.com/Flippylolz/WEF/pull/9).
- Independent result: schema/migration/seed can be verified through PostgreSQL and Compose before any public map contract changes.
- Affected code: Alembic environment/migration, persistence mappings, readiness, operator command, Compose migration/seed services, tests.
- Verification: clean/repeated upgrade, prior-proof upgrade, seed replay, indexes/constraints/PostGIS, readiness, full repository suite.

## Cross-task architecture

Infrastructure owns SQLAlchemy/Alembic mappings. Application/domain code owns enum/range/seed input semantics. Composition wires sessions; interfaces do not import ORM rows. E4 consumes narrow query ports rather than ORM entities. E0 proof persistence is removed after the replacement path passes.

## Data and migrations

- Implement only `locations` and `offers` fields required by M1; future migrations add lineage/media/auth tables.
- Use stable synthetic UUIDs and upserts so replay converges.
- The migration enables/verifies PostGIS, creates constraints/indexes, and writes no fixture rows.
- Seeding is a separate explicit command guarded against production.
- Migrations are forward-only; ordinary application rollback must remain schema compatible.

## Security and privacy

The fixture contains invented addresses/values only. It has no source text, phone, handle, raw payload, local path, media, session, provider response, or secret. Production never seeds automatically.

## Test and verification strategy

- Ruff/mypy/import-linter and unit tests for model/seed behavior.
- Disposable PostGIS integration tests for upgrade, replay, constraints, indexes, coordinate order, and migration-head readiness.
- Local Compose migration/seed/API smoke.
- Existing OpenAPI/frontend/image checks remain unchanged until downstream tasks.

## Operations, rollout, and rollback

Local Compose gates API startup on successful migration. Production migration integration belongs to E7 and must run under the deploy lock before app activation. Before production, rollback is branch/container cleanup. After migration use, never auto-downgrade or imply database recovery.

## Risks and mitigations

- **Competing proof model:** remove it in the same task after replacement tests pass.
- **Synthetic data mistaken for inventory:** stable synthetic labels and explicit operator-only command.
- **Migration blocks API:** readiness checks revision compatibility and Compose logs one-shot migration failure.
- **Future schema growth:** use additive forward revisions; do not prematurely add auth/media/source tables.

## Invalidation triggers

Return to the spike if M1 starts using real source/provider/media/auth data. Return to this plan if the approved model boundary remains but migration order, seed behavior, affected modules, or tests change materially.

## Approval checklist

- [x] E3 spike revision 2 is explicitly approved and current.
- [x] E3-T1 revision 2 is promoted with complete acceptance/traceability.
- [x] E1-T3 ancestry is recorded and acyclic.
- [x] Models, migration, tests, seed safety, rollout, and rollback limits are explicit.
- [x] D-002 and full ingestion/media/auth do not gate this synthetic-only boundary.
- [x] No implementation code was written before this plan approval.
- [x] Revision 2 records the approved plan.

## Owner decision

Flippylolz approved revision 2 through the delegated overnight MVP/autodeploy directive. It authorizes E3-T1 only after its dedicated branch/start gate; it does not authorize real-source ingestion, network geocoding, media, contacts, auth, or destructive production changes.
