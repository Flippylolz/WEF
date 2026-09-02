---
schema: ai-workflow/task@1
id: E23-T2
epic: E23
title: "Backfill non-verified location display names"
status: done
revision: 1
priority: P1
size: M
milestone: M5
dependencies: [E23-T1]
requirement_ids: [P-002, P-003, P-007]
decision_ids: [ADR-006, ADR-012]
deferred_decision_ids: []
promotion:
  source: ../proposed-tasks/E23-T2-display-name-backfill.md
  promoted_by: "Codex agent (owner-approved E23 spike revision 1)"
  promoted_at: "2026-09-02T17:34:00Z"
spike_gate:
  status: satisfied
  file: ../SPIKE.md
  approved_revision: 1
  verified_by: "Codex agent"
  verified_at: "2026-09-02T17:34:00Z"
implementation_gate:
  status: satisfied
  file: ../IMPLEMENTATION_PLAN.md
  approved_revision: 1
  verified_by: "Codex agent"
  verified_at: "2026-09-02T20:39:00Z"
dependency_gate:
  status: satisfied
  verified_by: "Codex agent"
  verified_at: "2026-09-02T20:39:00Z"
  evidence:
    - "E23-T1 implementation on feat/E23-T1-display-name-normalization / PR #316"
branch:
  required: true
  name: feat/E23-T2-display-name-backfill
  task_id: E23-T2
  one_task_only: true
  created_at: "2026-09-02T20:39:00Z"
  pull_request: https://github.com/Flippylolz/WEF/pull/317
completion:
  completed_by: "Codex agent"
  completed_at: "2026-09-02T19:10:00Z"
  pull_request: https://github.com/Flippylolz/WEF/pull/317
  evidence:
    - "../PRODUCTION_EVIDENCE.md"
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# E23-T2: Backfill non-verified location display names

## Outcome

Operators can dry-run and apply an idempotent rename of existing non-verified
locations to the E23-T1 canonical display-name rules using retained raw evidence,
without changing identity hashes or verified names.

## Scope

- Operator CLI with dry-run default and `--apply`.
- Scope writes to `display_name` / `display_address` only for locations whose
  `review_status` is not verified.
- Aggregate redacted before/after counts; hash-stability guardrails.
- Document the production runbook beside other operator commands.
- Route the three known fragment-only names as E18 curation cases when automatic
  normalization cannot produce a usable name.

## Out of scope

- Renaming verified locations.
- Near-suburb filter/badge UI.
- Re-geocoding or changing review status.

## Acceptance criteria

- [x] Dry-run reports changed/unchanged/skipped-verified/failure counts.
- [x] Apply is idempotent (`changed: 0` on re-run).
- [x] Verified locations are skipped.
- [x] `normalized_address_hash` never changes for processed rows.
- [x] Operator docs include the recommended production workflow.

## Dependencies and gates

- Depends on E23-T1.
- Blocked on owner approval of [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md).
