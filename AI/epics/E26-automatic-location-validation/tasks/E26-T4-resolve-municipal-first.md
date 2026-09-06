---
schema: ai-workflow/task@1
id: E26-T4
epic: E26
title: "Resolve locations from municipal data before hosted geocoding and AI"
status: done
revision: 1
priority: P1
size: M
milestone: M5
dependencies: [E26-T1, E26-T2, E26-T3]
requirement_ids: [P-001, P-003, P-004, P-007]
decision_ids: [ADR-003, ADR-005, ADR-012, ADR-021]
deferred_decision_ids: []
source: "owner-requested-municipal-first:2026-09-06"
promotion:
  source: ../MUNICIPAL_FIRST.md
  promoted_by: Codex
  promoted_at: "2026-09-06T15:24:20Z"
spike_gate:
  status: satisfied
  file: ../SPIKE.md
  approved_revision: 2
  verified_by: Codex
  verified_at: "2026-09-06T15:24:20Z"
implementation_gate:
  status: satisfied
  file: ../IMPLEMENTATION_PLAN.md
  approved_revision: 2
  verified_by: Codex
  verified_at: "2026-09-06T15:24:20Z"
dependency_gate:
  status: satisfied
  verified_by: Codex
  verified_at: "2026-09-06T15:24:20Z"
  evidence: ["E26-T1 done via PR #355", "E26-T2 done via PR #357", "E26-T3 done via PR #363; follow-up release 89c6a159f941c9ca491c52a30c09204f3fb20cd7 verified"]
branch:
  required: true
  name: feat/E26-T4-municipal-first
  task_id: E26-T4
  one_task_only: true
  created_at: "2026-09-06T15:24:20.540396+00:00"
  pull_request: https://github.com/Flippylolz/WEF/pull/369
completion:
  completed_by: Codex
  completed_at: "2026-09-06T18:25:58.996581+00:00"
  pull_request: https://github.com/Flippylolz/WEF/pull/371
  evidence: ["PRs #369–371 merged after current-head CI; release 34046973793 succeeded", "make verify passed on deployed implementation; six live municipal probes and nine canaries passed", "Owner explicitly authorized all-offers backfill; catalog-wide apply enabled and production/public checks passed; see T4_VERIFICATION.md"]
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# E26-T4: Municipal-first location resolution

Implement the owner-authorized [follow-up specification](../MUNICIPAL_FIRST.md). Ready before implementation; T1–T3 are done and deployed.

## Acceptance

- Municipal street geometry and numbered address points are authoritative when uniquely matched.
- Hosted fallback retains budgets and address/precision checks. AI only recovers source-supported address text, followed by verified lookup; never AI coordinates.
- Durable versioned caches, bounded attempts, restart behavior, owner protection and uncertainty are tested.
- Required local/CI gates pass; release succeeds; production observation identifies backfill needs before bounded application.

## Deployment verification

Implementation and bounded production verification passed. See [T4 verification](../T4_VERIFICATION.md). The owner explicitly authorized all-offers backfill; catalog-wide application is enabled and verified. Pending and quota-deferred work continues automatically under existing budgets.
