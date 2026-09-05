---
schema: ai-workflow/task@1
id: E27-T1
epic: E27
title: "Measure merge-to-production time and report release outcomes"
status: ready
revision: 1
priority: P1
size: M
milestone: M5
dependencies: []
requirement_ids: []
decision_ids: [ADR-008, ADR-009, ADR-010, ADR-013, ADR-014, ADR-017, ADR-023]
deferred_decision_ids: []
promotion:
  source: ../proposed-tasks/E27-T1-measure-release-and-report-outcomes.md
  promoted_by: codex
  promoted_at: "2026-09-05T10:18:07Z"
spike_gate:
  status: satisfied
  file: ../SPIKE.md
  approved_revision: 1
  verified_by: codex
  verified_at: "2026-09-05T10:18:07Z"
implementation_gate:
  status: satisfied
  file: ../IMPLEMENTATION_PLAN.md
  approved_revision: 1
  verified_by: codex
  verified_at: "2026-09-05T10:22:10Z"
dependency_gate:
  status: satisfied
  verified_by: codex
  verified_at: "2026-09-05T10:18:07Z"
  evidence: []
branch:
  required: true
  name: null
  task_id: E27-T1
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

# E27-T1: Measure merge-to-production time and report release outcomes

## Outcome

The owner sees whether a SHA was verified, skipped, queued, deployed, superseded, or failed, with timings that distinguish queue delay from work.

## Scope and work

Add machine-readable and human-readable stage outcomes and merge/run/healthy-version timestamps, explain failed deployment eligibility, and establish a baseline cohort of real merged-PR releases distinct from manual/direct-push runs.

Relevant seams are listed in the [epic spike](../SPIKE.md#research-method-and-evidence). The [audit](../../../audits/2026-09-05-system-audit.md) supplies the verified baseline and distinguishes source-confirmed risks from production observations.

## Acceptance criteria

- [ ] Release summaries explicitly distinguish verified-only success from deployment success and state the gate reason without exposing configuration or secrets.
- [ ] Measure mergedAt-to-healthy-version, event-to-start queue time, each verification/build stage, activation, rollback, and runner gaps; record unavailable timestamps rather than fabricating them.
- [ ] A direct push without an associated merged PR remains ineligible for automatic deployment, and an ordinary eligible merged PR needs no second dispatch.
- [ ] Collect at least 20 eligible ordinary release observations when available; report sample count, p50/p95, cold/warm/cache state, and queue time separately. The three audit samples remain illustrative, not a claimed population percentile.
- [ ] Notifications remain quiet for unchanged state and identify a meaningful deployment completion, failure, or required action; duplicate runs cannot report misleading fresh deployment.

## Tests and verification

Extend release-gate/proof tests for skipped deployment, missing PR association, failed verification, successful health check, and explicit unavailable timing data.

Run affected format/lint/type/test/contract checks, the [definition of done](../../../workflow/DEFINITION_OF_DONE.md), and `make lint` / `make test` before a push. Record exact commands and outcomes in the task PR. Use synthetic/sanitized fixtures and real persistence boundaries where the failure crosses transactions; no production fault injection is assumed.

## Dependencies and gates

No task dependency. Spike revision 1 is approved and this task is promoted. Implementation plan revision 1 is approved.

This promoted task is `ready` under the [workflow](../../../workflow/README.md) until its dependency gate clears. The [implementation plan](../IMPLEMENTATION_PLAN.md) specifies the modules, contracts, tests, budgets, and rollout for this task.

## Rollout and automatic operation

Add reporting first without changing execution order. Establish the baseline before optimizing so later timing claims use comparable events.

Normal successful work, contention/transient retry, and restart recovery must require no per-record owner action. Escalate only an unresolved material ambiguity, protected-value conflict, repeated systemic/access failure, or destructive recovery decision after the bounded automatic path has been exhausted.

## Rollback and recovery

Remove reporting hooks if they interfere with release execution while retaining fail-closed eligibility and existing logs.

## Risks and exclusions

A workflow completion timestamp is not necessarily the first healthy production version time. Report the measurement definition and limits.

Do not add production dependencies without owner approval, commit raw source/credentials, or mix unrelated refactoring into this task. General E14 infrastructure remains authoritative outside this task's specific regression/behavior scope.

## Promotion checklist

- [x] Current epic spike revision explicitly approved.
- [x] Scope, acceptance, dependencies, tests, risks, rollout, and rollback reviewed against that revision.
- [x] Required decisions resolved; dependencies remain enforceable in the planned sequence.
- [x] File moved, not copied, into `tasks/` with attributable promotion metadata.
- [ ] Dedicated branch and PR will cover this task only after implementation gates clear.
