---
schema: ai-workflow/task@1
id: E1-T2
epic: E1
title: "Scaffold web and backend applications"
status: in_progress
revision: 2
priority: P0
size: M
milestone: M1
dependencies: [E0-T2]
requirement_ids: []
decision_ids: [ADR-001, ADR-012, ADR-018]
deferred_decision_ids: []
promotion:
  source: ../proposed-tasks/E1-T2-scaffold-web-and-backend-applications.md
  promoted_by: "Cursor Agent (owner-authorized)"
  promoted_at: "2026-08-12T22:07:21Z"
spike_gate:
  status: satisfied
  file: ../SPIKE.md
  approved_revision: 2
  verified_by: "Cursor Agent"
  verified_at: "2026-08-12T22:07:21Z"
implementation_gate:
  status: satisfied
  file: ../IMPLEMENTATION_PLAN.md
  approved_revision: 4
  verified_by: "Cursor Agent"
  verified_at: "2026-08-12T22:07:21Z"
dependency_gate:
  status: stacked
  verified_by: "Cursor Agent"
  verified_at: "2026-08-12T22:07:21Z"
  evidence:
    - "E0-T2 | branch spike/E0-T2-architecture-proof | PR https://github.com/Flippylolz/WEF/pull/6 | head 7600ca8"
branch:
  required: true
  name: feature/E1-T2-application-scaffold
  task_id: E1-T2
  one_task_only: true
  created_at: "2026-08-12T22:07:21Z"
  pull_request: "https://github.com/Flippylolz/WEF/pull/7"
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

# E1-T2: Scaffold web and backend applications

## Outcome

Turn E0-T2's accepted synthetic proof into the reproducible backend/web application scaffold and documented command surface used by later product and Compose tasks.

## Scope

- Preserve E0-T2's runtime pins, lockfiles, generated-contract flow, package-by-feature boundaries, health behavior, and backend authority.
- Provide named development, build, and non-root runtime Dockerfile targets for the real FastAPI and Next.js commands.
- Add a thin root `Makefile` for existing install, format, lint, type-check, test, contract, and image-build commands.
- Smoke-test direct and container development/runtime startup without adding product behavior.

## Out of scope

- Docker Compose, production deployment, product map/filter/import features, production migrations/data, authentication, Telegram, and dependency automation.
- New framework/runtime choices or generic repository/service abstractions.

## Acceptance criteria

- [x] A frozen clean checkout installs, checks, tests, and builds both applications using documented real commands.
- [x] Backend and web Dockerfiles expose named development/build/runtime targets.
- [x] Development and production runtime targets start and return the expected live/page behavior.
- [x] Runtime images are non-root and exclude source data, media, credentials, development/documentation tooling, and build secrets.
- [x] The Makefile is a thin command façade with no business logic, hidden environment selection, or no-op target.
- [x] No application imports real source files through relative host paths.

## Test plan

- Run every Make target that does not require an external database; inspect target recipes for direct command mapping.
- Build every named Docker target and smoke `/api/v1/health/live` plus the web error/empty page.
- Inspect runtime users/content and Docker contexts.
- Re-run backend/frontend architecture, contract, lint, type, and unit tests.

## Verification evidence

- `make install format-check lint typecheck test contract-check build build-development` exercises every real-command target. The first run exposed and fixed a root-working-directory mypy invocation; the complete rerun passed.
- Backend: frozen uv install, Ruff, Import Linter, strict mypy, 14 local tests plus the E0 real-PostGIS result, coverage threshold, deterministic OpenAPI, and Redocly checks pass.
- Frontend: frozen pnpm install, Prettier, ESLint, strict TypeScript, Vitest, generated-contract currentness, static docs, and the production Next.js build pass.
- Dockerfiles now expose `development`, `build`, and `runtime`. Development and runtime containers were started on random loopback ports; API returned `{"status":"live"}` and web returned HTTP 200.
- Runtime smoke testing exposed and fixed a copied-virtualenv shebang path defect. The final backend image preserves `/build/.venv`, starts as `wef`, and contains no uv/pytest/mypy/Ruff; web starts as `node` without source/contracts/docs tooling.
- Git/Docker status includes only scaffold, lock, workflow, and documentation files. No real source/archive/media/session/credential path is imported or copied.

## Rollout and rollback

There is no production rollout. E1-T2 is a direct child of E0-T2. Before merge, close/revert this PR; after merge, use a normal revert. Do not rewrite shared history.

## Ready checklist

- [x] Promoted source, actor, timestamp, spike revision 2, and implementation-plan revision 4 are recorded.
- [x] E0-T2's open ancestor PR/head is recorded by `dependency_gate: stacked`.
- [x] Scope and acceptance match the approved plan.

## Start checklist

- [x] Status passed through `ready`.
- [x] Dedicated branch `feature/E1-T2-application-scaffold` contains E1-T2 only.
- [x] Branch name/time are recorded before `in_progress`.

## Done checklist

- [x] Acceptance criteria pass.
- [ ] The global [definition of done](../../../workflow/DEFINITION_OF_DONE.md) passes.
- [ ] Completion actor, time, pull request, and evidence are recorded.
