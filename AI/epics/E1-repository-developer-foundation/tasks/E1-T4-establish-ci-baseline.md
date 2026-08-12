---
schema: ai-workflow/task@1
id: E1-T4
epic: E1
title: "Establish CI baseline"
status: in_progress
revision: 1
priority: P0
size: M
milestone: M1
dependencies: [E1-T2]
requirement_ids: []
decision_ids: [ADR-009, ADR-012, ADR-013, ADR-017, ADR-018]
deferred_decision_ids: []
promotion:
  source: ../proposed-tasks/E1-T4-establish-ci-baseline.md
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
  verified_at: "2026-08-12T22:15:44Z"
  evidence:
    - "E1-T2 | branch feature/E1-T2-application-scaffold | PR https://github.com/Flippylolz/WEF/pull/7 | head 127f00c"
branch:
  required: true
  name: ci/E1-T4-baseline
  task_id: E1-T4
  one_task_only: true
  created_at: "2026-08-12T22:15:44Z"
  pull_request: "https://github.com/Flippylolz/WEF/pull/8"
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

# E1-T4: Establish CI baseline

## Outcome

Generalize the E0 proof workflow into stable synthetic repository checks and commit-addressed frontend contract artifacts.

## Scope

- Stable backend format/lint/type/unit/PostGIS/coverage/architecture/advisory checks.
- Stable frontend install/type/lint/test/build/advisory checks.
- Deterministic OpenAPI drift, Redocly, oasdiff compatibility, generated-client, and static artifact checks.
- Safe backend/web image builds, documentation-link validation, workflow linting, and deliberate failure probes.

## Out of scope

- GitHub-enforced branch protection, deployment, Dependabot merge automation, real source/production credentials, and product E2–E5 behavior.

## Acceptance criteria

- [ ] Representative lint, test, architecture, contract, documentation-link, or image failures block stable CI jobs.
- [x] Stale/breaking OpenAPI or generated frontend mismatch is rejected by the exact CI commands.
- [ ] OpenAPI JSON, generated TypeScript declarations, and static HTML are available in a commit-addressed artifact.
- [x] CI uses synthetic fixtures and no source/production credentials.
- [ ] Workflow/action syntax passes local lint and GitHub checks.

## Test plan

- Run action/workflow lint and every job locally where practical.
- Use temporary deliberate architecture/contract/docs drift probes and prove non-zero checks before cleanup.
- Inspect PR check names, logs, and artifact contents.

## Verification evidence

- `.github/workflows/ci.yml` defines stable `Backend`, `Frontend and contract`, `Repository safety`, and `Runtime images` jobs with read-only repository permissions.
- `actionlint` and `act -l` accept the final workflow and enumerate all four jobs.
- All underlying Make/backend/frontend/contract/advisory/image commands passed locally; the real PostGIS integration passed in E0-T2.
- `scripts/prove_contract_drift.py` temporarily changes OpenAPI, verifies generated currentness fails, restores exact bytes, and proves the clean check recovers.
- oasdiff 1.28.0 rejects a temporary removal of `GET /api/v1/estates`; the normal compatibility command passes against the available base.
- Import Linter rejects/cleans its deliberate domain framework violation. `scripts/check_markdown_links.py` validates every tracked relative Markdown target.
- Runtime checks build digest-pinned non-root images and inspect users plus absence of development/source/contract content.
- The artifact definition includes committed OpenAPI JSON, generated TypeScript, and standalone HTML under a commit-SHA name.
- GitHub Actions remains externally blocked: both the original workflow and a separate one-job `echo` parser smoke fail before job creation with `startup_failure`. See [B-006](../../../operations/BLOCKERS.md). Hosted check/artifact acceptance remains open.

## Rollout and rollback

CI only. Revert the workflow commit to roll back; never disable checks silently to merge a failing change.

## Ready checklist

- [x] Promotion and approval artifacts are recorded.
- [x] E1-T2 direct ancestor PR/head is recorded by a `stacked` dependency gate.
- [x] Scope and acceptance match implementation-plan revision 4.

## Start checklist

- [x] Status passed through `ready`.
- [x] Dedicated branch `ci/E1-T4-baseline` is created and recorded.
- [x] Branch contains E1-T4 only; its PR opens after checks pass.

## Done checklist

- [ ] Acceptance criteria pass.
- [ ] The global [definition of done](../../../workflow/DEFINITION_OF_DONE.md) passes.
- [ ] Completion actor, time, pull request, and evidence are recorded.
