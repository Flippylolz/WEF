---
schema: ai-workflow/task@1
id: E28-T5
epic: E28
title: Verify and monitor complete offer delivery
status: in_progress
revision: 1
priority: P1
size: M
milestone: M5
dependencies: [E28-T1, E28-T2, E28-T3, E28-T4]
requirement_ids: []
decision_ids: [ADR-006]
deferred_decision_ids: []
promotion:
  source: ../proposed-tasks/E28-T5-map-delivery-acceptance.md
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
  approved_revision: 7
  verified_by: Codex
  verified_at: "2026-09-08T06:48:39Z"
dependency_gate:
  status: stacked
  verified_by: Codex
  verified_at: "2026-09-08T08:02:00Z"
  evidence:
    - task_id: E28-T4
      branch: bugfix/E28-T4-recovered-offer-galleries
      pull_request: https://github.com/Flippylolz/WEF/pull/384
      head_commit: 30726abd2182ae63351f7548c69066249aa44d75
branch:
  required: true
  name: feat/E28-T5-map-delivery-acceptance
  task_id: E28-T5
  one_task_only: true
  created_at: "2026-09-08T08:02:00Z"
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

# E28-T5: Verify and monitor complete offer delivery

## Outcome and scope

Run bounded source-preserving recovery for the five audited offers through existing services, verify map and image responses, and add recent-offer delivery accounting/age alerts that catch parser, location and media blockers despite green transport. Record rollout and a 24-hour live acceptance window.

## Acceptance criteria

All five audited offer-bearing posts resolve to current public map offers with correct galleries and honest location precision. Old/source-media attempts cannot inflate denominators. Pipeline integration covers missed header to replay to offer/geocode/media/public API, edits/deletion, duplicate delivery and restart. New eligible offers deliver within five minutes under normal available provider budget; unresolved age/reason is reported when delayed. No manual per-offer routine is required.

## Modules, tests and operation

Follow the task-specific module boundary and rollout in [implementation plan revision 1](../IMPLEMENTATION_PLAN.md). Use invented fixtures, unit and real PostGIS integration tests; add contract/browser tests when public behavior changes. Run `make install`, `make lint`, `make test`, `make format-check`, `make typecheck`, and `make contract-check` before pushing affected implementation. Record exact results in the PR and task evidence.

Keep this change in its own task branch/PR; do not mark done before current-head CI and production acceptance pass. Roll back the immutable application release or pause only this recovery path, preserving raw revisions, owner selections and existing unrelated workloads. Do not claim application rollback undoes data changes. Operator repair receipts and current-source guards must support audit/recovery.

## Owner continuation

The owner requests full implementation and a backfill afterwards. Work on the
bounded operator and aggregate acceptance seams proceeds while predecessor PRs
are validated; application and completion remain blocked until T1–T4 release.
The old raw replay command selects linked offers only, so it cannot recover the
reported missing offers. This task adds a current-revision bounded operator using
the existing parser/persistence path, preserving live checkpoints and known
locations/visibility and existing field-origin protections.
