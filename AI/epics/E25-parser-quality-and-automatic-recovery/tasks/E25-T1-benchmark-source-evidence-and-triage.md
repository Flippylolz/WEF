---
schema: ai-workflow/task@1
id: E25-T1
epic: E25
title: "Benchmark source evidence and classify repairable gaps"
status: done
revision: 1
priority: P1
size: M
milestone: M5
dependencies: []
requirement_ids: [P-002, P-003, P-006, P-007]
decision_ids: [ADR-003, ADR-006, ADR-012]
deferred_decision_ids: []
promotion:
  source: ../proposed-tasks/E25-T1-benchmark-source-evidence-and-triage.md
  promoted_by: Codex
  promoted_at: "2026-09-05T10:15:52Z"
spike_gate:
  status: satisfied
  file: ../SPIKE.md
  approved_revision: 2
  verified_by: Codex
  verified_at: "2026-09-05T11:18:50Z"
implementation_gate:
  status: satisfied
  file: ../IMPLEMENTATION_PLAN.md
  approved_revision: 2
  verified_by: Codex
  verified_at: "2026-09-05T11:18:50Z"
dependency_gate:
  status: satisfied
  verified_by: Codex
  verified_at: "2026-09-05T11:18:50Z"
  evidence: []
branch:
  required: true
  name: feat/E25-T1-evidence-classification
  task_id: E25-T1
  one_task_only: true
  created_at: "2026-09-05T10:28:00Z"
  pull_request: https://github.com/Flippylolz/WEF/pull/328
completion:
  completed_by: Codex
  completed_at: "2026-09-05T15:01:37.460480+00:00"
  pull_request: https://github.com/Flippylolz/WEF/pull/328
  evidence:
    - ../E25-T1-IMPLEMENTATION_EVIDENCE.md
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null

---

# E25-T1: Benchmark source evidence and classify repairable gaps

## Outcome

The recovery queue represents genuine repairable listing problems, and field accuracy can be measured before parser rules change.

## Scope and work

Sample by source template/language/time, candidate score, visibility, parser version, and known gaps; create invented or safely anonymized regression equivalents. Define source-absent, expected non-offer/media, parser-miss, incomplete, conflicting, and provider-failure categories with unique source-revision denominators.

Relevant seams are listed in the [epic spike](../SPIKE.md#research-method-and-evidence). The [audit](../../../audits/2026-09-05-system-audit.md) supplies the verified baseline and distinguishes source-confirmed risks from production observations.

## Acceptance criteria

- [x] A versioned benchmark covers both owner-reported listings, dual-currency prices, price-per-area/add-ons, included storage, room tags, multilingual market/property types, and negative media/service/non-offer messages.
- [x] Report per-field exact-value accuracy and false positives against source-evidenced labels, plus candidate precision/recall and source-absent rates; do not equate all nulls or ledger rows with parser defects.
- [x] Expected non-offers do not enter the expensive recovery queue; a source-evidenced missing field can be detected even when extraction emitted no warning.
- [x] Repeated or unchanged source/version encounters deduplicate issue state; a newer successful parse resolves prior repairable issues automatically without erasing their history.
- [x] Publish only aggregate results and safe fixtures, with documented provenance and no raw exports, contacts, media, or source payloads in Git.

## Tests and verification

Add classification unit and persistence tests to the existing parse-issue ledger suite. Test a silent labeled-field miss, a non-listing message, an unchanged replay, and a later successful parser revision.

Run affected format/lint/type/test/contract checks, the [definition of done](../../../workflow/DEFINITION_OF_DONE.md), and `make lint` / `make test` before a push. Record exact commands and outcomes in the task PR. Use synthetic/sanitized fixtures and real persistence boundaries where the failure crosses transactions; no production fault injection is assumed.

## Dependencies and gates

No task dependency. Spike revision 1 is approved and promotion is recorded. Implementation-plan revision 1 is approved; the dedicated branch gate remains required.

This promoted task passed through `ready` in cc793bc and is now `in_progress` under the [workflow](../../../workflow/README.md). [Implementation plan revision 1](../IMPLEMENTATION_PLAN.md) is approved; the task must satisfy its dependency and branch gates before implementation.

## Rollout and automatic operation

Run new classification alongside the existing ledger to compare counts, then migrate queue eligibility in bounded batches.

Normal successful work, contention/transient retry, and restart recovery must require no per-record owner action. Escalate only an unresolved material ambiguity, protected-value conflict, repeated systemic/access failure, or destructive recovery decision after the bounded automatic path has been exhausted.

## Rollback and recovery

Retain old ledger entries and restore prior queue selection if new classification hides genuine candidates.

## Risks and exclusions

The existing 25,548 parser_miss count is not a labeled dataset. Benchmark labels need source evidence; ambiguous samples must be marked unresolved rather than guessed.

Do not add production dependencies without owner approval, commit raw source/credentials, or mix unrelated refactoring into this task. General E14 infrastructure remains authoritative outside this task's specific regression/behavior scope.

## Readiness and completion

- [x] Spike revision 1 approval and task promotion are recorded; the authoritative file is under `tasks/`.
- [x] Implementation plan revision 1 is explicitly approved and the implementation gate is satisfied.
- [x] This task has no dependencies; its dependency gate is satisfied.
- [x] Passed through `ready` in cc793bc and started on `feat/E25-T1-evidence-classification`.
- [x] Dedicated PR #328 is published; AD-053 records explicit merge and staged rollout authorization.
- [x] Acceptance criteria, required checks, healthy release and bounded production classification pass; completion evidence is recorded.

The documentation branch is not this task's implementation branch. Follow the task-specific modules, migration ownership, numeric limits, and verification requirements in [implementation plan revision 1](../IMPLEMENTATION_PLAN.md). Acceptance criteria above are preserved from proposed revision 1; promotion adds workflow metadata without changing their scope.

## Implementation evidence and publication gate

Local implementation and validation are recorded in [E25-T1 evidence](../E25-T1-IMPLEMENTATION_EVIDENCE.md). The source-evidence benchmark intentionally records remaining extraction failures for T2; this task does not repair canonical history or activate a provider.

Automatic approval review rejected pushing the E25 planning documents and opening a GitHub PR because it considered exporting that payload to GitHub insufficiently authorized. Both planning and T1 branches remain local pending explicit authorization to push them to `Flippylolz/WEF` and open PRs. T2/T3 cannot satisfy their stacked dependency gate until T1 has an open ancestor PR. T4 also retains E24-T1.

The completion record now includes merged PR #328, successful release 33973117645, and bounded production classification acceptance. Earlier publication-denial notes are historical.

## Provider revision gate

Spike and implementation plan revision 2 are explicitly owner-approved following the
[Batch/ZDR incompatibility](../PROVIDER_PRIVACY_REVISION.md). Prior test evidence
is retained; approval gates are restored explicitly to revision 2.

## Authorized release sequence

Publication succeeded as PR #328; prior publication-denial text above is historical.
AD-053 records the owner’s explicit E25 merge and staged production rollout approval.
All task acceptance criteria pass on the versioned fixtures and real PostGIS suite.
Current-main refresh passed 850 backend and 169 frontend tests; required CI passed
on `c6815b7`, including a successful retry after a PyPI connection reset. Latest-head
CI and release health remain required before the completion record is finalized.
