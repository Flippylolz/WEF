---
schema: ai-workflow/proposed-task@1
id: E24-T3
epic: E24
title: "Recover media independently after message commit"
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

# E24-T3: Recover media independently after message commit

## Outcome

A successfully persisted message eventually receives every eligible derivative even if downloading or media processing failed on the first attempt.

## Scope and work

Persist bounded media-work identity/outcome, reconstruct valid media descriptors, retry failures independently of message checksum changes, and preserve privacy-safe original/derivative storage boundaries.

Relevant seams are listed in the [epic spike](../SPIKE.md#research-method-and-evidence). The [audit](../../../audits/2026-09-05-system-audit.md) supplies the verified baseline and distinguishes source-confirmed risks from production observations.

## Acceptance criteria

- [ ] Crash injection after canonical commit but before media processing recovers derivatives automatically after restart, even when the message is unchanged.
- [ ] Historical, live, and album reconstruction preserve descriptor and association evidence; non-listing media does not attach to an unrelated offer.
- [ ] Repeated processing uses existing descriptor/revision/transform replay keys to produce one terminal disposition per intended asset and no duplicate public derivatives.
- [ ] Transient fetch/transform errors retry under bounded limits; unsupported/unsafe media becomes a terminal explained disposition rather than a permanent hidden retry loop.
- [ ] Text ingestion remains available during media-provider failure and reports media backlog separately; routine recovery requires no operator backfill command.

## Tests and verification

Extend test_telegram_live_media.py and live-event/storage integration tests. Replace the unconditional unchanged-media-skip expectation with completed-versus-pending media assertions.

Run affected format/lint/type/test/contract checks, the [definition of done](../../../workflow/DEFINITION_OF_DONE.md), and `make lint` / `make test` before a push. Record exact commands and outcomes in the task PR. Use synthetic/sanitized fixtures and real persistence boundaries where the failure crosses transactions; no production fault injection is assumed.

## Dependencies and gates

Required task dependencies: E24-T1. Their completed or valid stacked state must be proven before implementation begins; all must be done before completion/merge.

This candidate remains non-actionable under the [workflow](../../../workflow/README.md). It must move rather than copy to `tasks/`, retain its ID, and receive complete promotion and gate metadata.

## Rollout and automatic operation

Add the media ledger compatibly if required, then schedule unresolved work in bounded batches. Reconcile known terminal storage records before generating missing work.

Normal successful work, contention/transient retry, and restart recovery must require no per-record owner action. Escalate only an unresolved material ambiguity, protected-value conflict, repeated systemic/access failure, or destructive recovery decision after the bounded automatic path has been exhausted.

## Rollback and recovery

Pause media work while preserving canonical offers, original evidence, and successful derivatives. Do not remove public assets indiscriminately.

## Risks and exclusions

Missing media paths or historical local paths may need reacquisition from the source; classify unsupported cases without exposing paths or source contacts.

Do not add production dependencies without owner approval, commit raw source/credentials, or mix unrelated refactoring into this task. General E14 infrastructure remains authoritative outside this task's specific regression/behavior scope.

## Promotion checklist

- [ ] Current epic spike revision explicitly approved.
- [ ] Scope, acceptance, dependencies, tests, risks, rollout, and rollback reviewed against that revision.
- [ ] All referenced dependencies and required decisions resolved for the planned sequence.
- [ ] File moved, not copied, into `tasks/` with attributable promotion metadata.
- [ ] Dedicated branch and PR will cover this task only after implementation gates clear.
