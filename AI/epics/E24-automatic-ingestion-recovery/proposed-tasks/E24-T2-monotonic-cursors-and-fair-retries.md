---
schema: ai-workflow/proposed-task@1
id: E24-T2
epic: E24
title: "Make source cursors monotonic and retries fair"
status: proposed
revision: 1
actionable: false
priority: P1
size: L
milestone: M5
dependencies: [E24-T1]
requirement_ids: [P-006, P-007]
decision_ids: [ADR-003, ADR-005, ADR-006, ADR-007, ADR-012, ADR-015]
deferred_decision_ids: []
source: "owner-requested-system-audit:2026-09-05"
promotion:
  status: not_promoted
  target: null
  promoted_by: null
  promoted_at: null
---

# E24-T2: Make source cursors monotonic and retries fair

## Outcome

Passive events, polling, and archive recovery share a cursor that never moves backward and a retry policy that distinguishes contention from corrupt data.

## Scope and work

Define a durable channel high-water cursor, lock/read/update ordering, per-item retry scheduling, bounded backoff and jitter, and fair work selection. Reconcile old edits/deletes within explicitly supported source-access bounds.

Relevant seams are listed in the [epic spike](../SPIKE.md#research-method-and-evidence). The [audit](../../../audits/2026-09-05-system-audit.md) supplies the verified baseline and distinguishes source-confirmed risks from production observations.

## Acceptance criteria

- [ ] A deterministic race where polling advances the cursor before older archive work gets the lock leaves the persisted cursor unchanged at the higher value.
- [ ] Lower-ID edits and deletions are applied without decreasing the channel high-water cursor; status and runtime read the same committed meaning.
- [ ] RunLockHeldError and provider/transport deferrals do not exhaust the malformed-record budget; eligible jobs resume automatically after contention clears.
- [ ] A poisoned event cannot starve later events, and an exhausted record has one actionable exception record with reason, evidence, and an automatic re-evaluation trigger.
- [ ] An outage/overlap test covers new records and older edits/deletes under a documented bounded reconciliation policy; unsupported source-history gaps are visible and not falsely marked complete.

## Tests and verification

Extend test_telegram_reconciliation.py, test_telegram_worker_ops.py, and database integration tests with controlled concurrent tasks. Verify restart, lock contention, stale cursors, monotonicity, and retry fairness.

Run affected format/lint/type/test/contract checks, the [definition of done](../../../workflow/DEFINITION_OF_DONE.md), and `make lint` / `make test` before a push. Record exact commands and outcomes in the task PR. Use synthetic/sanitized fixtures and real persistence boundaries where the failure crosses transactions; no production fault injection is assumed.

## Dependencies and gates

Required task dependencies: E24-T1. Their completed or valid stacked state must be proven before implementation begins; all must be done before completion/merge.

This candidate remains non-actionable under the [workflow](../../../workflow/README.md). It must move rather than copy to `tasks/`, retain its ID, and receive complete promotion and gate metadata.

## Rollout and automatic operation

If a cursor/retry schema is needed, deploy additively and derive its initial state from verified channel evidence. Observe old/new status parity before switching authoritative reads.

Normal successful work, contention/transient retry, and restart recovery must require no per-record owner action. Escalate only an unresolved material ambiguity, protected-value conflict, repeated systemic/access failure, or destructive recovery decision after the bounded automatic path has been exhausted.

## Rollback and recovery

Retain the highest verified cursor and per-event ledger. Pause the affected consumer rather than resetting progress to the newest run's arbitrary checkpoint.

## Risks and exclusions

Using MAX(message_id) alone may skip holes. High-water progress needs reconciliation evidence, not an assumption that every lower ID is an offer.

Do not add production dependencies without owner approval, commit raw source/credentials, or mix unrelated refactoring into this task. General E14 infrastructure remains authoritative outside this task's specific regression/behavior scope.

## Promotion checklist

- [ ] Current epic spike revision explicitly approved.
- [ ] Scope, acceptance, dependencies, tests, risks, rollout, and rollback reviewed against that revision.
- [ ] All referenced dependencies and required decisions resolved for the planned sequence.
- [ ] File moved, not copied, into `tasks/` with attributable promotion metadata.
- [ ] Dedicated branch and PR will cover this task only after implementation gates clear.
