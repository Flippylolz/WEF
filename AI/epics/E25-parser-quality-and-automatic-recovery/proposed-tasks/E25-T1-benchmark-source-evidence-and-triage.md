---
schema: ai-workflow/proposed-task@1
id: E25-T1
epic: E25
title: "Benchmark source evidence and classify repairable gaps"
status: proposed
revision: 1
actionable: false
priority: P1
size: M
milestone: M5
dependencies: []
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

# E25-T1: Benchmark source evidence and classify repairable gaps

## Outcome

The recovery queue represents genuine repairable listing problems, and field accuracy can be measured before parser rules change.

## Scope and work

Sample by source template/language/time, candidate score, visibility, parser version, and known gaps; create invented or safely anonymized regression equivalents. Define source-absent, expected non-offer/media, parser-miss, incomplete, conflicting, and provider-failure categories with unique source-revision denominators.

Relevant seams are listed in the [epic spike](../SPIKE.md#research-method-and-evidence). The [audit](../../../audits/2026-09-05-system-audit.md) supplies the verified baseline and distinguishes source-confirmed risks from production observations.

## Acceptance criteria

- [ ] A versioned benchmark covers both owner-reported listings, dual-currency prices, price-per-area/add-ons, included storage, room tags, multilingual market/property types, and negative media/service/non-offer messages.
- [ ] Report per-field exact-value accuracy and false positives against source-evidenced labels, plus candidate precision/recall and source-absent rates; do not equate all nulls or ledger rows with parser defects.
- [ ] Expected non-offers do not enter the expensive recovery queue; a source-evidenced missing field can be detected even when extraction emitted no warning.
- [ ] Repeated or unchanged source/version encounters deduplicate issue state; a newer successful parse resolves prior repairable issues automatically without erasing their history.
- [ ] Publish only aggregate results and safe fixtures, with documented provenance and no raw exports, contacts, media, or source payloads in Git.

## Tests and verification

Add classification unit and persistence tests to the existing parse-issue ledger suite. Test a silent labeled-field miss, a non-listing message, an unchanged replay, and a later successful parser revision.

Run affected format/lint/type/test/contract checks, the [definition of done](../../../workflow/DEFINITION_OF_DONE.md), and `make lint` / `make test` before a push. Record exact commands and outcomes in the task PR. Use synthetic/sanitized fixtures and real persistence boundaries where the failure crosses transactions; no production fault injection is assumed.

## Dependencies and gates

No task dependency. Current epic spike approval, task promotion, and implementation-plan approval are still required before implementation.

This candidate remains non-actionable under the [workflow](../../../workflow/README.md). It must move rather than copy to `tasks/`, retain its ID, and receive complete promotion and gate metadata.

## Rollout and automatic operation

Run new classification alongside the existing ledger to compare counts, then migrate queue eligibility in bounded batches.

Normal successful work, contention/transient retry, and restart recovery must require no per-record owner action. Escalate only an unresolved material ambiguity, protected-value conflict, repeated systemic/access failure, or destructive recovery decision after the bounded automatic path has been exhausted.

## Rollback and recovery

Retain old ledger entries and restore prior queue selection if new classification hides genuine candidates.

## Risks and exclusions

The existing 25,548 parser_miss count is not a labeled dataset. Benchmark labels need source evidence; ambiguous samples must be marked unresolved rather than guessed.

Do not add production dependencies without owner approval, commit raw source/credentials, or mix unrelated refactoring into this task. General E14 infrastructure remains authoritative outside this task's specific regression/behavior scope.

## Promotion checklist

- [ ] Current epic spike revision explicitly approved.
- [ ] Scope, acceptance, dependencies, tests, risks, rollout, and rollback reviewed against that revision.
- [ ] All referenced dependencies and required decisions resolved for the planned sequence.
- [ ] File moved, not copied, into `tasks/` with attributable promotion metadata.
- [ ] Dedicated branch and PR will cover this task only after implementation gates clear.
