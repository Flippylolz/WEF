---
schema: ai-workflow/task@1
id: E24-T4
epic: E24
title: "Verify ingestion progress and automate recovery escalation"
status: in_progress
revision: 2
priority: P1
size: M
milestone: M5
dependencies: [E24-T1, E24-T2]
requirement_ids: [P-006, P-007]
decision_ids: [ADR-003, ADR-005, ADR-006, ADR-007, ADR-012, ADR-015]
deferred_decision_ids: []
promotion:
  source: ../proposed-tasks/E24-T4-verify-progress-and-automate-recovery.md
  promoted_by: Codex
  promoted_at: "2026-09-06T05:30:10.288298+00:00"
spike_gate:
  status: satisfied
  file: ../SPIKE.md
  approved_revision: 2
  verified_by: Codex
  verified_at: "2026-09-06T05:30:10.288298+00:00"
implementation_gate:
  status: satisfied
  file: ../IMPLEMENTATION_PLAN.md
  approved_revision: 4
  verified_by: Codex
  verified_at: "2026-09-06T05:30:10.288298+00:00"
dependency_gate:
  status: satisfied
  verified_by: Codex
  verified_at: "2026-09-06T05:30:10.288298+00:00"
  evidence:
    - "T1/T2 done; PRODUCTION_EVIDENCE.md. T3 contracts deployed via PR #346; owner explicitly approved independent T4 sequencing."
branch:
  required: true
  name: feat/E24-T4-progress-monitoring
  task_id: E24-T4
  one_task_only: true
  created_at: "2026-09-06T05:32:58.775865+00:00"
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

Required task dependencies: E24-T1, E24-T2. T3 deployed ledger/status contracts are verified prerequisites; its separate production repair acceptance remains open. Their completed or valid stacked state must be proven before implementation begins; all must be done before completion/merge.

Promoted after owner approval of implementation-plan revision 4 and its explicit sequencing change.

## Rollout and automatic operation

Observe new progress signals before making them health gates. Reuse worker supervision and publish bounded redacted diagnostic fields.

Normal successful work, contention/transient retry, and restart recovery must require no per-record owner action. Escalate only an unresolved material ambiguity, protected-value conflict, repeated systemic/access failure, or destructive recovery decision after the bounded automatic path has been exhausted.

## Rollback and recovery

Disable the new recovery trigger if it amplifies load; keep read-only progress diagnostics and durable work state.

## Risks and exclusions

An idle source and a stalled worker are different conditions. Alerts must use pending eligible work and deadlines, not time since the last listing alone.

Do not add production dependencies without owner approval, commit raw source/credentials, or mix unrelated refactoring into this task. General E14 infrastructure remains authoritative outside this task's specific regression/behavior scope.

## Promotion checklist

- [x] Current epic spike revision explicitly approved.
- [x] Scope, acceptance, dependencies, tests, risks, rollout, and rollback reviewed against that revision.
- [x] All referenced dependencies and required decisions resolved for the planned sequence.
- [x] File moved, not copied, into `tasks/` with attributable promotion metadata.
- [ ] Dedicated branch and PR will cover this task only after implementation gates clear.

## Concrete monitoring proposal

The [revision 4 proposal](../T4_MONITORING_PROPOSAL.md) defines stage-specific
progress, durable counters, deadline-aware stall detection, incident deduplication
and the 24-hour acceptance window. It proposes an explicit owner-approved
sequencing change; the current dependencies and non-actionable state remain
unchanged until that approval is recorded.

## Implementation evidence

The dedicated T4 implementation adds durable minute snapshots, deadline-aware
classification, incident lifecycle and private observation/activation controls.
Existing T2 cursor/retry regressions are retained. New tests cover repeated terminal
work, idle/provider/lease distinctions, transaction rollback, competing monitors,
retention, activation gaps, episode recovery, policy/receipt eligibility and query
timeout isolation from canonical landing. The 24-hour result cannot complete T3.

T4 remains `in_progress` through local validation, green CI, the 15-minute initial
production observation and the full 24-hour acceptance window. No completion claim
is made by this implementation record.
