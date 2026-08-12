---
schema: ai-workflow/task@1
id: E1-T4
epic: E1
title: "Establish CI baseline"
status: draft
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
  status: blocked
  verified_by: null
  verified_at: null
  evidence: []
branch:
  required: true
  name: null
  task_id: E1-T4
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
- [ ] Stale/breaking OpenAPI or generated frontend mismatch blocks CI.
- [ ] OpenAPI JSON, generated TypeScript declarations, and static HTML are available in a commit-addressed artifact.
- [ ] CI uses synthetic fixtures and no source/production credentials.
- [ ] Workflow/action syntax passes local lint and GitHub checks.

## Test plan

- Run action/workflow lint and every job locally where practical.
- Use temporary deliberate architecture/contract/docs drift probes and prove non-zero checks before cleanup.
- Inspect PR check names, logs, and artifact contents.

## Rollout and rollback

CI only. Revert the workflow commit to roll back; never disable checks silently to merge a failing change.

## Ready checklist

- [x] Promotion and approval artifacts are recorded.
- [ ] E1-T2 direct ancestor PR/head is recorded by a `stacked` dependency gate.
- [x] Scope and acceptance match implementation-plan revision 4.

## Start checklist

- [ ] Status passed through `ready`.
- [ ] Dedicated branch is created and recorded.
- [ ] Branch/PR contain E1-T4 only.

## Done checklist

- [ ] Acceptance criteria pass.
- [ ] The global [definition of done](../../../workflow/DEFINITION_OF_DONE.md) passes.
- [ ] Completion actor, time, pull request, and evidence are recorded.
