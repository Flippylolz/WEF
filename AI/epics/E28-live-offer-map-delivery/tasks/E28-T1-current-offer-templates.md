---
schema: ai-workflow/task@1
id: E28-T1
epic: E28
title: Recognize current offer templates
status: done
revision: 1
priority: P1
size: M
milestone: M5
dependencies: []
requirement_ids: []
decision_ids: [ADR-006]
deferred_decision_ids: []
promotion:
  source: ../proposed-tasks/E28-T1-current-offer-templates.md
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
  status: satisfied
  verified_by: Codex
  verified_at: "2026-09-08T06:48:39Z"
  evidence: []
branch:
  required: true
  name: bugfix/E28-T1-current-offer-templates
  task_id: E28-T1
  one_task_only: true
  created_at: "2026-09-08T06:52:17Z"
  pull_request: https://github.com/Flippylolz/WEF/pull/377
completion:
  completed_by: Codex
  completed_at: "2026-09-08T07:42:00Z"
  pull_request: https://github.com/Flippylolz/WEF/pull/377
  evidence:
    - ../T1_VERIFICATION.md
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# E28-T1: Recognize current offer templates

## Outcome and scope

Recognize evidence-bearing Russian apartment/house headers and Cyrillic area signals; extract separately labeled apartment/house totals, parking/storage amounts and bounded inline room counts. Extend independent parse-quality evidence so future silent misses are recoverable. Version the parser/policy. Do not change geographic scope or weaken AI apply validation.

## Acceptance criteria

Invented equivalents of the latest header/price families parse correctly with exact provenance. Unit-price, rent/service prose, addon-only amounts, conflicting totals/rooms, media-only messages and existing benchmark negatives cannot become false price/offer positives. Real persistence verifies expected price minor units and idempotent source/offer links. Scope remains honest: the house can be detected before T3 resolves its locality.

## Modules, tests and operation

Follow the task-specific module boundary and rollout in [implementation plan revision 1](../IMPLEMENTATION_PLAN.md). Use invented fixtures, unit and real PostGIS integration tests; add contract/browser tests when public behavior changes. Run `make install`, `make lint`, `make test`, `make format-check`, `make typecheck`, and `make contract-check` before pushing affected implementation. Record exact results in the PR and task evidence.

Keep this change in its own task branch/PR; do not mark done before current-head CI and production acceptance pass. Roll back the immutable application release or pause only this recovery path, preserving raw revisions, owner selections and existing unrelated workloads. Do not claim application rollback undoes data changes. Operator repair receipts and current-source guards must support audit/recovery.

## Start evidence

Passed through `ready` in planning commit `cba13bd`. Dedicated branch created from current main with the completed documentation baseline before implementation.

## Local implementation evidence

[Verification](../T1_VERIFICATION.md) records the 1,378 backend and 186 frontend passing tests, the bounded frontend retry, source comparison and remaining rollout boundary.
