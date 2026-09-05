---
schema: ai-workflow/proposed-task@1
id: E25-T4
epic: E25
title: "Converge parser versions and field provenance automatically"
status: proposed
revision: 1
actionable: false
priority: P1
size: L
milestone: M5
dependencies: [E24-T1, E25-T2, E25-T3]
requirement_ids: [P-002, P-003, P-006, P-007]
decision_ids: [ADR-003, ADR-006, ADR-012]
deferred_decision_ids: []
source: "owner-requested-system-audit:2026-09-05"
promotion:
  status: not_promoted
  target: null
  promoted_by: null
  promoted_at: null
---

# E25-T4: Converge parser versions and field provenance automatically

## Outcome

Deploying an accepted parser/policy version automatically repairs eligible historical records and closes their issues with stable identities and correct provenance.

## Scope and work

Schedule bounded version-aware replay after release, keep parser and source revision identities separate, refresh extraction/field provenance, preserve protected values, and reconcile issue/offer/filter changes.

Relevant seams are listed in the [epic spike](../SPIKE.md#research-method-and-evidence). The [audit](../../../audits/2026-09-05-system-audit.md) supplies the verified baseline and distinguishes source-confirmed risks from production observations.

## Acceptance criteria

- [ ] A release with a new parser version discovers stale eligible records automatically; a second run on unchanged source/version produces zero canonical changes.
- [ ] Every updated field traces to the current parser version and source evidence even when the source revision was unchanged; offer-source provenance cannot silently remain on the old extractor.
- [ ] Offer IDs, favorites, source links, contacts, deleted/hidden state, owner-verified values, and AI field protection survive replay; source edits cannot be overwritten by stale work.
- [ ] Replay reports considered, source-absent, updated, deferred, protected-conflict, and failed populations with a balanced denominator; version distributions converge for eligible rows.
- [ ] Historical replay yields to live ingestion under bounded resource/provider budgets, resumes after restart, and needs no routine backfill dispatch.

## Tests and verification

Database integration tests cover parser-only revision changes, current-source revision races, idempotency, protected origin conflicts, stable offer identity, and catalog facet/filter consistency.

Run affected format/lint/type/test/contract checks, the [definition of done](../../../workflow/DEFINITION_OF_DONE.md), and `make lint` / `make test` before a push. Record exact commands and outcomes in the task PR. Use synthetic/sanitized fixtures and real persistence boundaries where the failure crosses transactions; no production fault injection is assumed.

## Dependencies and gates

Required task dependencies: E24-T1, E25-T2, E25-T3. Their completed or valid stacked state must be proven before implementation begins; all must be done before completion/merge.

This candidate remains non-actionable under the [workflow](../../../workflow/README.md). It must move rather than copy to `tasks/`, retain its ID, and receive complete promotion and gate metadata.

## Rollout and automatic operation

Requires E24-T1 before production replay. Use a small automatic canary cohort, validate value/provenance/visibility diffs, and expand in checkpointed batches.

Normal successful work, contention/transient retry, and restart recovery must require no per-record owner action. Escalate only an unresolved material ambiguity, protected-value conflict, repeated systemic/access failure, or destructive recovery decision after the bounded automatic path has been exhausted.

## Rollback and recovery

Pause scheduling, preserve the release/version ledger, and restore only changed fields whose origins still match the reverted replay; do not restore whole production tables.

## Risks and exclusions

Some legacy/operator/synthetic records are intentionally excluded from deterministic replay. Exclusions must be explicit and countable rather than preventing completion indefinitely.

Do not add production dependencies without owner approval, commit raw source/credentials, or mix unrelated refactoring into this task. General E14 infrastructure remains authoritative outside this task's specific regression/behavior scope.

## Promotion checklist

- [ ] Current epic spike revision explicitly approved.
- [ ] Scope, acceptance, dependencies, tests, risks, rollout, and rollback reviewed against that revision.
- [ ] All referenced dependencies and required decisions resolved for the planned sequence.
- [ ] File moved, not copied, into `tasks/` with attributable promotion metadata.
- [ ] Dedicated branch and PR will cover this task only after implementation gates clear.
