---
schema: ai-workflow/task@1
id: E28-T2
epic: E28
title: Resolve valid Warsaw street locations
status: in_progress
revision: 2
priority: P1
size: M
milestone: M5
dependencies: [E28-T1]
requirement_ids: []
decision_ids: [ADR-006]
deferred_decision_ids: []
promotion:
  source: ../proposed-tasks/E28-T2-warsaw-street-resolution.md
  promoted_by: Codex
  promoted_at: "2026-09-08T06:48:39Z"
spike_gate:
  status: satisfied
  file: ../SPIKE.md
  approved_revision: 1
  verified_by: Codex
  verified_at: "2026-09-08T06:48:39Z"
implementation_gate:
  status: satisfied
  file: ../IMPLEMENTATION_PLAN.md
  approved_revision: 5
  verified_by: Codex
  verified_at: "2026-09-08T06:48:39Z"
dependency_gate:
  status: satisfied
  verified_by: Codex
  verified_at: "2026-09-08T06:48:39Z"
  evidence:
    - task_id: E28-T1
      branch: bugfix/E28-T1-current-offer-templates
      pull_request: https://github.com/Flippylolz/WEF/pull/377
      head_commit: 7bb566cd00d13d70ef5e2f584b7cb289934d219a
branch:
  required: true
  name: bugfix/E28-T2-warsaw-street-resolution
  task_id: E28-T2
  one_task_only: true
  created_at: "2026-09-08T07:09:17.634182+00:00"
  pull_request: https://github.com/Flippylolz/WEF/pull/380
completion:
  completed_by: null
  completed_at: null
  pull_request: https://github.com/Flippylolz/WEF/pull/380
  evidence: []
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# E28-T2: Resolve valid Warsaw street locations

## Outcome and scope

Recognize reviewed Warsaw neighborhoods as neighborhoods, preserving Warsaw city evidence and district agreement. Inspect municipal identity/segmentation and resolve street-only offers using verified same-street geometry. Version normalization/review targets for retry of stale terminal results; preserve protected selections and real ambiguity.

## Acceptance criteria

Invented Sielce-style cases agree with matching Warsaw provider evidence; actual city/district/street mismatches still fail. Multiple segments of one verified street yield one truthful street-level position; distinct streets/districts never collapse. Aignera and Szeligowska pass canary revalidation and appear through the public map API. Test stale-source, protected-selection and replay failure cases.

## Modules, tests and operation

Follow the task-specific module boundary and rollout in [implementation plan revision 1](../IMPLEMENTATION_PLAN.md). Use invented fixtures, unit and real PostGIS integration tests; add contract/browser tests when public behavior changes. Run `make install`, `make lint`, `make test`, `make format-check`, `make typecheck`, and `make contract-check` before pushing affected implementation. Record exact results in the PR and task evidence.

Keep this change in its own task branch/PR; do not mark done before current-head CI and production acceptance pass. Roll back the immutable application release or pause only this recovery path, preserving raw revisions, owner selections and existing unrelated workloads. Do not claim application rollback undoes data changes. Operator repair receipts and current-source guards must support audit/recovery.

## Start evidence

Passed through ready under the approved spike; implementation plan revision 2 authorizes the explicit T1 stack, verified against open, mergeable PR #377 at the recorded head.
