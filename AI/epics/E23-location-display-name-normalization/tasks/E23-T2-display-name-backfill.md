---
schema: ai-workflow/task@1
id: E23-T2
epic: E23
title: "Backfill non-verified location display names"
status: draft
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
  task_id: E23-T2
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

- [ ] Dry-run reports changed/unchanged/skipped-verified/failure counts.
- [ ] Apply is idempotent (`changed: 0` on re-run).
- [ ] Verified locations are skipped.
- [ ] `normalized_address_hash` never changes for processed rows.
- [ ] Operator docs include the recommended production workflow.

## Dependencies and gates

- Depends on E23-T1.
- Blocked on owner approval of [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md).
