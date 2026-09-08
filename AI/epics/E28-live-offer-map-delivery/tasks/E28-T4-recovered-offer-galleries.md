---
schema: ai-workflow/task@1
id: E28-T4
epic: E28
title: Reconnect galleries after offer recovery
status: draft
revision: 1
priority: P1
size: M
milestone: M5
dependencies: [E28-T1]
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
  approved_revision: 1
  verified_by: Codex
  verified_at: "2026-09-08T06:48:39Z"
dependency_gate:
  status: blocked
  verified_by: null
  verified_at: null
  evidence: []
branch:
  required: true
  name: null
  task_id: E28-T4
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

# E28-T4: Reconnect galleries after offer recovery

## Outcome and scope

Make existing unassociated discovery outcomes eligible after a canonical offer link appears. Reuse explicit album/reply evidence and bounded established grouping rules, reconcile current revisions, and preserve immutable media verification. Handle edits/restarts and superseded descriptor quarantines without bypassing byte/source equivalence checks.

## Acceptance criteria

A previously missed listing followed by media gains exactly its own gallery after offer recovery, with idempotent restart/replay and no cross-album leaks. Current and superseded revision counts are separate. Existing completed assets are reused; missing derivatives and genuinely changed source media have distinct outcomes. Deleted/stale/protected associations remain fenced.

## Modules, tests and operation

Follow the task-specific module boundary and rollout in [implementation plan revision 1](../IMPLEMENTATION_PLAN.md). Use invented fixtures, unit and real PostGIS integration tests; add contract/browser tests when public behavior changes. Run `make install`, `make lint`, `make test`, `make format-check`, `make typecheck`, and `make contract-check` before pushing affected implementation. Record exact results in the PR and task evidence.

Keep this change in its own task branch/PR; do not mark done before current-head CI and production acceptance pass. Roll back the immutable application release or pause only this recovery path, preserving raw revisions, owner selections and existing unrelated workloads. Do not claim application rollback undoes data changes. Operator repair receipts and current-source guards must support audit/recovery.
