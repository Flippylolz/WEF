---
schema: ai-workflow/task@1
id: E28-T3
epic: E28
title: Support source-evidenced nearby localities
status: in_progress
revision: 3
priority: P1
size: M
milestone: M5
dependencies: [E28-T1, E28-T2]
requirement_ids: []
decision_ids: [ADR-006]
deferred_decision_ids: []
promotion:
  source: ../proposed-tasks/E28-T3-nearby-localities.md
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
  approved_revision: 6
  verified_by: Codex
  verified_at: "2026-09-08T06:48:39Z"
dependency_gate:
  status: stacked
  verified_by: Codex
  verified_at: "2026-09-08T07:25:00Z"
  evidence:
    - task_id: E28-T1
      branch: bugfix/E28-T1-current-offer-templates
      pull_request: https://github.com/Flippylolz/WEF/pull/377
      head_commit: 7bb566cd00d13d70ef5e2f584b7cb289934d219a
    - task_id: E28-T2
      branch: bugfix/E28-T2-avenue-address-matching
      pull_request: https://github.com/Flippylolz/WEF/pull/386
      head_commit: 566ee74d0aea44f3402902c901ca707f61c1f03f
branch:
  required: true
  name: feat/E28-T3-district-area-delivery
  task_id: E28-T3
  one_task_only: true
  created_at: "2026-09-08T07:25:00Z"
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

# E28-T3: Support source-evidenced nearby localities

## Outcome and scope

Retain explicit nearby locality/municipality/country from offer pin lines; stop injecting Warsaw. Define a bounded nearby-Warsaw scope covering the audited Dosin/Serock case, version cache/revalidation identity, and expose truthful locality precision on the public map. Reuse current provider and budgets; no new production dependency.

## Acceptance criteria

The Dosin acceptance offer is located in its evidenced locality rather than Warsaw. Invented nearby-town, ambiguous same-name town, misleading marketing mention and city-only fixtures cover extraction through persistence, public map filtering and precision display. The default map allows discovery of supported nearby offers. Unknown exact addresses are never represented as building precision. Contract/migration checks run if affected.

## Modules, tests and operation

Follow the task-specific module boundary and rollout in [implementation plan revision 1](../IMPLEMENTATION_PLAN.md). Use invented fixtures, unit and real PostGIS integration tests; add contract/browser tests when public behavior changes. Run `make install`, `make lint`, `make test`, `make format-check`, `make typecheck`, and `make contract-check` before pushing affected implementation. Record exact results in the PR and task evidence.

Keep this change in its own task branch/PR; do not mark done before current-head CI and production acceptance pass. Roll back the immutable application release or pause only this recovery path, preserving raw revisions, owner selections and existing unrelated workloads. Do not claim application rollback undoes data changes. Operator repair receipts and current-source guards must support audit/recovery.

## Start evidence

Owner continuation authorizes the full epic and subsequent backfill. T1 is merged
in main; this dependent branch contains it and proceeds while production release
acceptance is pending. Completion remains gated on that acceptance.

## District-only delivery follow-up

Plan revision 5 adds source-supported municipal district areas to the same
truthful coarse-location path. T2 avenue follow-up #386 is the immediate stack
parent. Existing town, street, building and protected selections remain covered.
