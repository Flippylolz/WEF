---
schema: ai-workflow/proposed-task@1
id: E24-T4
epic: E24
title: "Verify ingestion progress and automate recovery escalation"
status: proposed
revision: 1
actionable: false
priority: P1
size: M
milestone: M5
dependencies: [E24-T1, E24-T2, E24-T3]
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

# E24-T4: Verify ingestion progress and automate recovery escalation

## Outcome

Ingestion detects and resolves routine stalls automatically; only exhausted or systemic failures reach the owner.

## Scope and work

Add ingestion-specific unique-completion/backlog-age/retry/media-lag metrics and one aggregate status model. Integrate with existing worker supervision; expose signals for E14-T6 without building a duplicate monitoring platform.

Relevant seams are listed in the [epic spike](../SPIKE.md#research-method-and-evidence). The [audit](../../../audits/2026-09-05-system-audit.md) supplies the verified baseline and distinguishes source-confirmed risks from production observations.

## Acceptance criteria

- [ ] A worker that repeatedly processes the same terminal sibling is unhealthy for archive progress even while transport and source-head checks pass.
- [ ] Counters distinguish fetched, attempted, uniquely committed, terminally classified, deferred, and media-complete work; reconciliation balances those populations.
- [ ] Transient outage and contention tests recover automatically, then clear their incident state without a manual acknowledgement.
- [ ] Alerts deduplicate a systemic failure; unchanged/non-actionable state produces no recurring per-record owner notifications.
- [ ] After bounded remediation, record a 24-hour evidence window with no repeating terminal work, a non-growing eligible backlog at ordinary load, and zero routine operator interventions.

## Tests and verification

Unit-test status calculations with a fake clock; integrate backlog and failure-recovery tests against PostGIS. Preserve public readiness independence from worker freshness.

Run affected format/lint/type/test/contract checks, the [definition of done](../../../workflow/DEFINITION_OF_DONE.md), and `make lint` / `make test` before a push. Record exact commands and outcomes in the task PR. Use synthetic/sanitized fixtures and real persistence boundaries where the failure crosses transactions; no production fault injection is assumed.

## Dependencies and gates

Required task dependencies: E24-T1, E24-T2, E24-T3. Their completed or valid stacked state must be proven before implementation begins; all must be done before completion/merge.

This candidate remains non-actionable under the [workflow](../../../workflow/README.md). It must move rather than copy to `tasks/`, retain its ID, and receive complete promotion and gate metadata.

## Rollout and automatic operation

Observe new progress signals before making them health gates. Reuse worker supervision and publish bounded redacted diagnostic fields.

Normal successful work, contention/transient retry, and restart recovery must require no per-record owner action. Escalate only an unresolved material ambiguity, protected-value conflict, repeated systemic/access failure, or destructive recovery decision after the bounded automatic path has been exhausted.

## Rollback and recovery

Disable the new recovery trigger if it amplifies load; keep read-only progress diagnostics and durable work state.

## Risks and exclusions

An idle source and a stalled worker are different conditions. Alerts must use pending eligible work and deadlines, not time since the last listing alone.

Do not add production dependencies without owner approval, commit raw source/credentials, or mix unrelated refactoring into this task. General E14 infrastructure remains authoritative outside this task's specific regression/behavior scope.

## Promotion checklist

- [ ] Current epic spike revision explicitly approved.
- [ ] Scope, acceptance, dependencies, tests, risks, rollout, and rollback reviewed against that revision.
- [ ] All referenced dependencies and required decisions resolved for the planned sequence.
- [ ] File moved, not copied, into `tasks/` with attributable promotion metadata.
- [ ] Dedicated branch and PR will cover this task only after implementation gates clear.
