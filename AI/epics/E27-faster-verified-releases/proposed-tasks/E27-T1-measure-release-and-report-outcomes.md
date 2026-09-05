---
schema: ai-workflow/proposed-task@1
id: E27-T1
epic: E27
title: "Measure merge-to-production time and report release outcomes"
status: proposed
revision: 1
actionable: false
priority: P1
size: M
milestone: M5
dependencies: []
requirement_ids: []
decision_ids: [ADR-008, ADR-009, ADR-010, ADR-013, ADR-014, ADR-017, ADR-023]
deferred_decision_ids: []
source: "owner-requested-system-audit:2026-09-05"
promotion:
  status: not_promoted
  target: null
  promoted_by: null
  promoted_at: null
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

No task dependency. Current epic spike approval, task promotion, and implementation-plan approval are still required before implementation.

This candidate remains non-actionable under the [workflow](../../../workflow/README.md). It must move rather than copy to `tasks/`, retain its ID, and receive complete promotion and gate metadata.

## Rollout and automatic operation

Add reporting first without changing execution order. Establish the baseline before optimizing so later timing claims use comparable events.

Normal successful work, contention/transient retry, and restart recovery must require no per-record owner action. Escalate only an unresolved material ambiguity, protected-value conflict, repeated systemic/access failure, or destructive recovery decision after the bounded automatic path has been exhausted.

## Rollback and recovery

Remove reporting hooks if they interfere with release execution while retaining fail-closed eligibility and existing logs.

## Risks and exclusions

A workflow completion timestamp is not necessarily the first healthy production version time. Report the measurement definition and limits.

Do not add production dependencies without owner approval, commit raw source/credentials, or mix unrelated refactoring into this task. General E14 infrastructure remains authoritative outside this task's specific regression/behavior scope.

## Promotion checklist

- [ ] Current epic spike revision explicitly approved.
- [ ] Scope, acceptance, dependencies, tests, risks, rollout, and rollback reviewed against that revision.
- [ ] All referenced dependencies and required decisions resolved for the planned sequence.
- [ ] File moved, not copied, into `tasks/` with attributable promotion metadata.
- [ ] Dedicated branch and PR will cover this task only after implementation gates clear.
