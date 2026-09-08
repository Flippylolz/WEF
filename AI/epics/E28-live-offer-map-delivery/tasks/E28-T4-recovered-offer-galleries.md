---
schema: ai-workflow/task@1
id: E28-T4
epic: E28
title: Reconnect galleries after offer recovery
status: in_progress
revision: 2
priority: P1
size: M
milestone: M5
dependencies: [E28-T1, E28-T3]
requirement_ids: []
decision_ids: [ADR-006]
deferred_decision_ids: []
promotion:
  source: ../proposed-tasks/E28-T4-recovered-offer-galleries.md
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
  approved_revision: 4
  verified_by: Codex
  verified_at: "2026-09-08T06:48:39Z"
dependency_gate:
  status: stacked
  verified_by: Codex
  verified_at: "2026-09-08T07:34:00Z"
  evidence:
    - task_id: E28-T1
      branch: bugfix/E28-T1-current-offer-templates
      pull_request: https://github.com/Flippylolz/WEF/pull/377
      head_commit: 7bb566cd00d13d70ef5e2f584b7cb289934d219a
    - task_id: E28-T3
      branch: feat/E28-T3-nearby-localities
      pull_request: https://github.com/Flippylolz/WEF/pull/383
      head_commit: fe78314463317e92294abf6b4d72aa3036ba06f3
branch:
  required: true
  name: bugfix/E28-T4-recovered-offer-galleries
  task_id: E28-T4
  one_task_only: true
  created_at: "2026-09-08T07:34:00Z"
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

# E28-T4: Reconnect galleries after offer recovery

## Outcome and scope

Make existing unassociated discovery outcomes eligible after a canonical offer link appears. Reuse explicit album/reply evidence and bounded established grouping rules, reconcile current revisions, and preserve immutable media verification. Handle edits/restarts and superseded descriptor quarantines without bypassing byte/source equivalence checks.

## Acceptance criteria

A previously missed listing followed by media gains exactly its own gallery after offer recovery, with idempotent restart/replay and no cross-album leaks. Current and superseded revision counts are separate. Existing completed assets are reused; missing derivatives and genuinely changed source media have distinct outcomes. Deleted/stale/protected associations remain fenced.

## Modules, tests and operation

Follow the task-specific module boundary and rollout in [implementation plan revision 1](../IMPLEMENTATION_PLAN.md). Use invented fixtures, unit and real PostGIS integration tests; add contract/browser tests when public behavior changes. Run `make install`, `make lint`, `make test`, `make format-check`, `make typecheck`, and `make contract-check` before pushing affected implementation. Record exact results in the PR and task evidence.

Keep this change in its own task branch/PR; do not mark done before current-head CI and production acceptance pass. Roll back the immutable application release or pause only this recovery path, preserving raw revisions, owner selections and existing unrelated workloads. Do not claim application rollback undoes data changes. Operator repair receipts and current-source guards must support audit/recovery.

## Start evidence

Owner continuation authorizes full implementation and backfill. This main-based
branch includes merged T1; production acceptance remains pending. An additive
per-link discovery receipt is needed to detect canonical owners created after the
chronological media scan, including AI-created offers, without polling terminal
media forever or changing source evidence.
