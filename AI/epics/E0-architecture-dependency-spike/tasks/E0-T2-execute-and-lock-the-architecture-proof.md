---
schema: ai-workflow/task@1
id: E0-T2
epic: E0
title: "Execute and lock the architecture proof"
status: draft
revision: 2
priority: P0
size: M
milestone: M1
dependencies: [E0-T1, E1-T1]
requirement_ids: []
decision_ids: [ADR-001, ADR-005, ADR-012, ADR-013, ADR-018]
deferred_decision_ids: []
promotion:
  source: ../proposed-tasks/E0-T2-execute-and-lock-the-architecture-proof.md
  promoted_by: "Cursor Agent (owner-authorized)"
  promoted_at: "2026-08-12T21:03:00Z"
spike_gate:
  status: satisfied
  file: ../SPIKE.md
  approved_revision: 2
  verified_by: "Cursor Agent"
  verified_at: "2026-08-12T21:03:00Z"
implementation_gate:
  status: satisfied
  file: ../IMPLEMENTATION_PLAN.md
  approved_revision: 3
  verified_by: "Cursor Agent"
  verified_at: "2026-08-12T21:03:00Z"
dependency_gate:
  status: blocked
  verified_by: null
  verified_at: null
  evidence: []
branch:
  required: true
  name: null
  task_id: E0-T2
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

# E0-T2: Execute and lock the architecture proof

> Promoted after explicit owner approval of E0 spike revision 2 and implementation-plan revision 3. This task remains `draft` until the E0-T1 pull request provides direct stack ancestry, dependency evidence is updated, and the task becomes `ready` then `in_progress` on its dedicated branch. Under ADR-018, dependencies may remain `stacked` while implementation proceeds, but they must be `done` before this task completes or merges.

## Outcome

Produce a synthetic, reproducible proof of the approved backend-centric architecture and lock the dependency/runtime baseline used by later scaffolding.

## Scope

- Implement only the synthetic proof and deliverables defined by [spike revision 2](../SPIKE.md).
- Pin supported runtimes and direct dependencies; produce reproducible `uv` and `pnpm` lockfiles.
- Record dependency purposes, licenses, advisories, replacement paths, and measured install/build/test evidence.
- Demonstrate route/query-or-interactor/port/adapter/application-DTO/presenter flow with no domain rule duplicated in the frontend.
- Add architecture import checks, PostGIS integration, deterministic OpenAPI export, generated TypeScript client usage, English i18n, and Docker build verification.

## Out of scope

- Real source exports, media, contacts, credentials, Telegram sessions, or production services.
- General product features beyond the minimum synthetic vertical proof.
- Local multi-service Compose topology, which remains E1-T3 after E1-T2.
- Production deployment or environment configuration.

## Affected modules and contracts

- Future `apps/backend`, `apps/web`, and root dependency/runtime manifests.
- `contracts/openapi/v1.json` and generated frontend contract checks.
- [Architecture](../../../architecture/README.md), [OpenAPI contract](../../../contracts/OPENAPI.md), and [ADR-012](../../../decisions/adr/ADR-012-backend-centric-modular-monolith.md).

## Implementation notes

- Use explicit constructors and the composition root; infrastructure implements inward-owned ports.
- Keep transport, ORM, and presentation types outside the domain.
- Use named multi-stage Dockerfile targets, locked installs, non-root runtime users, and safe BuildKit behavior from the approved spike.
- Do not create a throwaway placeholder service or pre-empt E1-T3's Compose scope.
- Resolve FastAPI Users, `nuqs`, PostGIS test strategy, and factory choice from measured proof evidence and record any departure.

## Acceptance criteria

- [ ] Route → query/interactor → port/adapter → application DTO → presenter is demonstrated without domain logic in the frontend.
- [ ] A targeted proof CI workflow runs checks, and `import-linter` rejects a deliberate dependency violation.
- [ ] PostGIS integration, deterministic OpenAPI generation, generated TypeScript request, Next.js rendering, and English i18n proof pass.
- [ ] `contracts/openapi/v1.json`, Redocly lint/static docs, `oasdiff`, and production-disabled documentation routes follow the OpenAPI contract.
- [ ] Runtime/dependency versions, purposes, licenses, advisories, replacement paths, and lockfile reproducibility are recorded.
- [ ] Docker builds pass with safe contexts and contain no source data, media, credentials, production values, or documentation generators in runtime layers.
- [ ] The proof touches no real source data, media, credentials, or production service.

## Test plan

- Unit: domain/value/application behavior in the synthetic module.
- Integration: real PostGIS adapter and transaction behavior.
- Architecture: import-linter contracts plus a deliberate forbidden import fixture.
- Contract: deterministic OpenAPI export, Redocly, `oasdiff`, generated TypeScript compile/request.
- Frontend: thin rendering and English i18n behavior.
- Build/security: locked clean installs, Docker image builds, license/advisory scans, and context/image-content checks.

## Rollout and rollback

There is no production rollout. The proof becomes the scaffold baseline for E1-T2 only after acceptance. A failed dependency or architecture choice is reverted on this task branch and documented; a material direction change returns to the E0 spike gate.

## Ready checklist

- [x] The file is authoritative under `tasks/`; the proposed definition is removed during this promotion.
- [x] Promotion source, promoter, and timestamp are recorded.
- [x] `spike_gate` references owner-approved spike revision 2 and is `satisfied`.
- [x] `implementation_gate` references owner-approved implementation-plan revision 3 and is `satisfied`.
- [ ] E0-T1 and E1-T1 are `done`, with dependency evidence recorded.
- [ ] Scope and acceptance criteria match the approved plan.

## Start checklist

- [ ] Status passed through `ready`.
- [ ] One new branch contains `E0-T2`.
- [ ] The branch and pull request contain this task only.
- [ ] `branch.name` and `branch.created_at` are recorded before setting `in_progress`.

## Done checklist

- [ ] Acceptance criteria pass.
- [ ] The global [definition of done](../../../workflow/DEFINITION_OF_DONE.md) passes.
- [ ] Completion actor, time, pull request, and evidence are recorded.
