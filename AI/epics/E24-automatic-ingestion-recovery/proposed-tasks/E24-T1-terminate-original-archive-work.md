---
schema: ai-workflow/proposed-task@1
id: E24-T1
epic: E24
title: "Terminate original archive work and repair starvation"
status: proposed
revision: 1
actionable: false
priority: P1
size: L
milestone: M5
dependencies: []
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

# E24-T1: Terminate original archive work and repair starvation

## Outcome

Each original archived event reaches its own terminal outcome once, and later queued records make progress without repeated processing of reconstructed siblings.

## Scope and work

Fix original-record acknowledgement, lossless reconstruction or direct archived-input processing, outcome correlation, idempotency, and bounded reconciliation of affected pending/sibling rows. Preserve original payload and checksum evidence.

Relevant seams are listed in the [epic spike](../SPIKE.md#research-method-and-evidence). The [audit](../../../audits/2026-09-05-system-audit.md) supplies the verified baseline and distinguishes source-confirmed risks from production observations.

## Acceptance criteria

- [ ] A PostGIS regression using a historical payload with photo/entity fields and a differently shaped live payload proves the original record becomes terminal and the next oldest batch advances.
- [ ] Success, intentional non-candidate, canonical failure, cancellation after commit, and acknowledgement failure have explicit outcomes; restart completes pending work without duplicate offers or revisions.
- [ ] Replay cannot replace a newer canonical source revision with an older archive version, or resurrect a deleted offer. Add ordered old/new/edit/delete cases.
- [ ] An automated preflight reports eligible backlog, terminal siblings, oldest age, and proposed transitions; bounded application reconciles every changed row and re-running makes zero additional changes.
- [ ] A fixed production window shows unique pending work decreasing and terminal rows no longer accumulating attempts every cycle. Record exclusions and source-preservation checks without raw payloads.

## Tests and verification

Extend test_telegram_live_events.py and database-backed archive/persistence tests. Existing fake-archive tests must be complemented by real unique-checksum constraints and actual payload reconstruction. Include a restart/commit-boundary failure case.

Run affected format/lint/type/test/contract checks, the [definition of done](../../../workflow/DEFINITION_OF_DONE.md), and `make lint` / `make test` before a push. Record exact commands and outcomes in the task PR. Use synthetic/sanitized fixtures and real persistence boundaries where the failure crosses transactions; no production fault injection is assumed.

## Dependencies and gates

No task dependency. Current epic spike approval, task promotion, and implementation-plan approval are still required before implementation.

This candidate remains non-actionable under the [workflow](../../../workflow/README.md). It must move rather than copy to `tasks/`, retain its ID, and receive complete promotion and gate metadata.

## Rollout and automatic operation

Deploy the acknowledgement fix before any broad backfill. Enable bounded automatic reconciliation with durable progress and a pause switch; preserve a restricted before/after transition ledger.

Normal successful work, contention/transient retry, and restart recovery must require no per-record owner action. Escalate only an unresolved material ambiguity, protected-value conflict, repeated systemic/access failure, or destructive recovery decision after the bounded automatic path has been exhausted.

## Rollback and recovery

Pause draining/reconciliation on evidence mismatch and retain all originals. Roll back code only to a version that cannot resume the known looping path; do not delete sibling rows to make counters look correct.

## Risks and exclusions

Clearing every pending row because a sibling exists could falsely acknowledge an unrelated revision. Correlate exact source/event semantics and downstream outcomes.

Do not add production dependencies without owner approval, commit raw source/credentials, or mix unrelated refactoring into this task. General E14 infrastructure remains authoritative outside this task's specific regression/behavior scope.

## Promotion checklist

- [ ] Current epic spike revision explicitly approved.
- [ ] Scope, acceptance, dependencies, tests, risks, rollout, and rollback reviewed against that revision.
- [ ] All referenced dependencies and required decisions resolved for the planned sequence.
- [ ] File moved, not copied, into `tasks/` with attributable promotion metadata.
- [ ] Dedicated branch and PR will cover this task only after implementation gates clear.
