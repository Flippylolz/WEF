---
schema: ai-workflow/task@1
id: E1-T4
epic: E1
title: "Establish CI baseline"
status: done
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
  status: satisfied
  verified_by: "Cursor Agent (owner-authorized reconciliation)"
  verified_at: "2026-08-13T17:44:22Z"
  evidence:
    - "E1-T2 | done | merged PR https://github.com/Flippylolz/WEF/pull/7 | merge 07ee778"
branch:
  required: true
  name: ci/E1-T4-baseline
  task_id: E1-T4
  one_task_only: true
  created_at: "2026-08-12T22:15:44Z"
  pull_request: "https://github.com/Flippylolz/WEF/pull/8"
completion:
  completed_by: "Flippylolz (owner-authorized reconciliation)"
  completed_at: "2026-08-13T14:52:42Z"
  pull_request: "https://github.com/Flippylolz/WEF/pull/8"
  evidence:
    - "Task PR merged into the ordered stack at f766a63517b6ba49a1377e630ea54e9cb4e0e56f"
    - "All four integrated main CI jobs passed: https://github.com/Flippylolz/WEF/actions/runs/31726996540"
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

- [x] Representative lint, test, architecture, contract, documentation-link, or image failures block stable CI jobs.
- [x] Stale/breaking OpenAPI or generated frontend mismatch is rejected by the exact CI commands.
- [x] OpenAPI JSON, generated TypeScript declarations, and static HTML are available in a commit-addressed artifact.
- [x] CI uses synthetic fixtures and no source/production credentials.
- [x] Workflow/action syntax passes local lint and GitHub checks.

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
- GitHub Actions recovered after the initial B-006 startup failure. The integrated `main` run completed Backend, Frontend and contract, Repository safety, and Runtime images successfully and published the commit-addressed contract artifact.

## Rollout and rollback

CI only. Revert the workflow commit to roll back; never disable checks silently to merge a failing change.

## Ready checklist

- [x] Promotion and approval artifacts are recorded.
- [x] E1-T2 completion evidence is recorded by a satisfied dependency gate.
- [x] Scope and acceptance match implementation-plan revision 4.

## Start checklist

- [x] Status passed through `ready`.
- [x] Dedicated branch `ci/E1-T4-baseline` is created and recorded.
- [x] Branch contains E1-T4 only; its PR opens after checks pass.

## Done checklist

- [x] Acceptance criteria pass.
- [x] The global [definition of done](../../../workflow/DEFINITION_OF_DONE.md) passes.
- [x] Completion actor, time, pull request, and evidence are recorded.
