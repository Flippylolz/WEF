---
schema: ai-workflow/task@1
id: E0-T2
epic: E0
title: "Execute and lock the architecture proof"
status: in_progress
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
  status: stacked
  verified_by: "Cursor Agent"
  verified_at: "2026-08-12T21:37:55Z"
  evidence:
    - "E1-T1 | branch chore/E1-T1-repository-safety | roll-up PR https://github.com/Flippylolz/WEF/pull/4 | head 0c2e242"
    - "E0-T1 | branch docs/E0-T1-architecture-review | PR https://github.com/Flippylolz/WEF/pull/5 | head df0a38b"
branch:
  required: true
  name: spike/E0-T2-architecture-proof
  task_id: E0-T2
  one_task_only: true
  created_at: "2026-08-12T21:37:55Z"
  pull_request: "https://github.com/Flippylolz/WEF/pull/6"
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

> Promoted after explicit owner approval of E0 spike revision 2 and implementation-plan revision 3. This proof is `in_progress` on its dedicated branch above the recorded E1-T1 and E0-T1 pull requests. Under ADR-018, dependencies may remain `stacked` while implementation proceeds, but they must be `done` before this task completes or merges.

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

- [x] Route → query/interactor → port/adapter → application DTO → presenter is demonstrated without domain logic in the frontend.
- [ ] A targeted proof CI workflow runs checks, and `import-linter` rejects a deliberate dependency violation.
- [x] PostGIS integration, deterministic OpenAPI generation, generated TypeScript request, Next.js rendering, and English i18n proof pass.
- [x] `contracts/openapi/v1.json`, Redocly lint/static docs, `oasdiff`, and production-disabled documentation routes follow the OpenAPI contract.
- [x] Runtime/dependency versions, purposes, licenses, advisories, replacement paths, and lockfile reproducibility are recorded.
- [x] Docker builds pass with safe contexts and contain no source data, media, credentials, production values, or documentation generators in runtime layers.
- [x] The proof touches no real source data, media, credentials, or production service.

## Test plan

- Unit: domain/value/application behavior in the synthetic module.
- Integration: real PostGIS adapter and transaction behavior.
- Architecture: import-linter contracts plus a deliberate forbidden import fixture.
- Contract: deterministic OpenAPI export, Redocly, `oasdiff`, generated TypeScript compile/request.
- Frontend: thin rendering and English i18n behavior.
- Build/security: locked clean installs, Docker image builds, license/advisory scans, and context/image-content checks.

## Verification evidence

The measured dependency conclusions and full command results are recorded in the [E0-T2 proof report](../PROOF_REPORT.md).

- Backend: Ruff and strict mypy pass; Import Linter keeps all three contracts and rejects/cleans a deliberate domain-to-FastAPI violation.
- Tests: 15 backend tests pass against a disposable PostGIS 17/3.5 container with 96.10% branch-aware coverage; 3 frontend Vitest tests pass.
- Contract: deterministic OpenAPI export, generated TypeScript currentness, typed `openapi-fetch` request, Redocly lint/static HTML, and oasdiff checks pass. Runtime schema/Swagger/ReDoc routes are absent.
- Frontend: strict TypeScript, ESLint, fixed-English Server/Client next-intl rendering, and the Next.js production build pass without reimplementing availability logic.
- Supply chain: uv/pnpm frozen locks pass; pip-audit and production pnpm audit report no known vulnerabilities; direct dependency licenses and replacement paths are recorded.
- Images: digest-pinned backend and web builds pass. Runtime users are `wef` and `node`; backend development tools and frontend source/contracts/documentation generators are absent.
- Safety: only synthetic fixtures and the disposable local PostGIS container were used. No real export, media, credential, Telegram session, or production service was read.
- CI: `.github/workflows/e0-architecture-proof.yml` reproduces backend/PostGIS, architecture, contract, frontend, advisory, and image checks in [PR #6](https://github.com/Flippylolz/WEF/pull/6).

## Rollout and rollback

There is no production rollout. The proof becomes the scaffold baseline for E1-T2 only after acceptance. A failed dependency or architecture choice is reverted on this task branch and documented; a material direction change returns to the E0 spike gate.

## Ready checklist

- [x] The file is authoritative under `tasks/`; the proposed definition is removed during this promotion.
- [x] Promotion source, promoter, and timestamp are recorded.
- [x] `spike_gate` references owner-approved spike revision 2 and is `satisfied`.
- [x] `implementation_gate` references owner-approved implementation-plan revision 3 and is `satisfied`.
- [x] E0-T1 and E1-T1 have open/integration ancestor pull requests recorded by `dependency_gate: stacked`; completion still requires both to be `done`.
- [x] Scope and acceptance criteria match the approved plan.

## Start checklist

- [x] Status passed through `ready`.
- [x] One new branch contains `E0-T2`.
- [x] The branch contains E0-T2 only; its pull request is opened after verification.
- [x] `branch.name` and `branch.created_at` were recorded before setting `in_progress`.

## Done checklist

- [ ] Acceptance criteria pass.
- [ ] The global [definition of done](../../../workflow/DEFINITION_OF_DONE.md) passes.
- [ ] Completion actor, time, pull request, and evidence are recorded.
