---
schema: ai-workflow/task@1
id: E0-T1
epic: E0
title: Replace with task title
status: draft
revision: 1
priority: P0
size: S
milestone: M1
dependencies: []
requirement_ids: []
decision_ids: []
deferred_decision_ids: []
promotion:
  source: ../proposed-tasks/E0-T1-replace-with-slug.md
  promoted_by: null
  promoted_at: null
spike_gate:
  status: blocked
  file: ../SPIKE.md
  approved_revision: null
  verified_by: null
  verified_at: null
implementation_gate:
  status: blocked
  file: ../IMPLEMENTATION_PLAN.md
  approved_revision: null
  verified_by: null
  verified_at: null
dependency_gate:
  status: blocked
  verified_by: null
  verified_at: null
  evidence: []
branch:
  required: true
  name: null
  task_id: E0-T1
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

# E0-T1: Replace with task title

> Create this file by moving/refining its proposed-task definition after spike approval. Replace example values and complete promotion metadata. Do not set `ready` until every gate is satisfied; do not write code until the task is `in_progress` on its dedicated branch.

## Outcome

State the single independently reviewable result.

## Scope

- List included work exactly as covered by the approved implementation plan.

## Out of scope

- List explicit exclusions and follow-up tasks.

## Affected modules and contracts

- Link expected modules, public/persisted contracts, migrations, and domain documents.

## Implementation notes

Describe task-specific constraints from the approved plan. A material departure invalidates the affected approval; it is not authorized by editing this section alone.

## Acceptance criteria

- [ ] Add objective, testable criteria preserved/refined from the proposed task.

## Test plan

- Unit:
- Integration:
- Contract/migration:
- End-to-end:
- Security/accessibility/operations:

## Rollout and rollback

State migration order, feature/operational activation, health checks, rollback boundaries, and data-recovery limits as applicable.

## Ready checklist

- [ ] The file is authoritative under `tasks/`; no duplicate remains under `proposed-tasks/`.
- [ ] Promotion source, promoter, and timestamp are recorded.
- [ ] `spike_gate` references the owner-approved current spike revision and is `satisfied`.
- [ ] `implementation_gate` references the owner-approved current implementation-plan revision, which contains this task ID/current revision, and is `satisfied`.
- [ ] Every dependency is `done` with `dependency_gate: satisfied`, or each incomplete dependency is an ancestor PR recorded by `dependency_gate: stacked`; every deferred gate is resolved.
- [ ] Scope and acceptance criteria match the approved plan.

## Start checklist

- [ ] Status passed through `ready`.
- [ ] One new branch contains this task ID.
- [ ] The branch and pull request contain this task only.
- [ ] `branch.name` and `branch.created_at` are recorded before setting `in_progress`.

## Done checklist

- [ ] Acceptance criteria pass.
- [ ] The global [definition of done](../DEFINITION_OF_DONE.md) passes.
- [ ] Completion actor, time, pull request, and evidence are recorded.

Gate `status` values are exactly `blocked`, `stacked`, `satisfied`, or `invalidated`; only a dependency gate may be `stacked`. A stacked task cannot be completed or merged until dependencies are `done` and the gate becomes `satisfied`. Task state values and transition rules are defined in the [workflow](../README.md).
