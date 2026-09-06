---
schema: ai-workflow/task@1
id: E26-T1
epic: E26
title: "Validate address agreement and source-supported precision"
status: done
revision: 2
priority: P1
size: L
milestone: M5
dependencies: []
requirement_ids: [P-001, P-003, P-004, P-007]
decision_ids: [ADR-003, ADR-005, ADR-012, ADR-021]
deferred_decision_ids: []
source: "owner-requested-system-audit:2026-09-05"
promotion:
  source: ../proposed-tasks/E26-T1-validate-address-agreement-and-precision.md
  promoted_by: Codex
  promoted_at: "2026-09-06T05:28:07Z"
spike_gate:
  status: satisfied
  file: ../SPIKE.md
  approved_revision: 1
  verified_by: Codex
  verified_at: "2026-09-06T05:28:07Z"
implementation_gate:
  status: satisfied
  file: ../IMPLEMENTATION_PLAN.md
  approved_revision: 1
  verified_by: Codex
  verified_at: "2026-09-06T05:33:04Z"
dependency_gate:
  status: satisfied
  verified_by: Codex
  verified_at: "2026-09-06T05:28:07Z"
  evidence: []
branch:
  required: true
  name: bugfix/E26-T1-address-agreement
  task_id: E26-T1
  one_task_only: true
  created_at: "2026-09-06T05:33:04Z"
  pull_request: https://github.com/Flippylolz/WEF/pull/355
completion:
  completed_by: Codex
  completed_at: "2026-09-06T06:38:26Z"
  pull_request: https://github.com/Flippylolz/WEF/pull/355
  evidence: ["Merge 6722ecb79d47958a92eb3608aeade1a4a3cede9e", "Release run 34016504593 succeeded", "T1_VERIFICATION.md; 1204 backend and 169 frontend tests passed"]
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# E26-T1: Validate address agreement and source-supported precision

## Outcome

A provider result on the wrong street cannot become an accepted exact-looking pin merely because it has a high score or falls inside the Warsaw bounding box.

## Scope and work

Version structured source/provider address evidence, normalize neighborhoods/districts/city separately, evaluate bounded candidate sets and ambiguity, validate geographic scope, and replace automatic blanket pending-pin acceptance with the accepted accuracy policy.

Relevant seams are listed in the [epic spike](../SPIKE.md#research-method-and-evidence). The [audit](../../../audits/2026-09-05-system-audit.md) supplies the verified baseline and distinguishes source-confirmed risks from production observations.

## Acceptance criteria

- [x] The Jugosłowiańska-to-Grochowska-town-hall regression is rejected or retried despite provider confidence 1.00; amenity classification cannot supply unsupported building precision.
- [x] Gocław is resolved as a neighborhood within the Warsaw context rather than displayed as a replacement city; both source variants preserve street tokens and source text provenance.
- [x] Street/house-number/locality agreement is required at the claimed precision; missing numbers never become invented building-level matches, and a neighborhood centroid never claims to locate the requested street.
- [x] Low-confidence and low-precision results receive bounded automatic normalization/candidate retries with versioned evidence; unresolved ambiguity is explicit and does not trigger endless provider requests.
- [x] Actor/reason lineage distinguishes automatic decisions from genuine owner review; tests cover wrong street, duplicate street names, incompatible district, out-of-scope result, cache hit, quota limit, and manual verified override.

## Tests and verification

Extend test_geocoding.py, test_geocoding_integration.py, test_accept_pending_geocode_pins.py, and recurring-worker tests with sanitized provider payloads for the three audited cases and negative address matches.

Run affected format/lint/type/test/contract checks, the [definition of done](../../../workflow/DEFINITION_OF_DONE.md), and `make lint` / `make test` before a push. Record exact commands and outcomes in the task PR. Use synthetic/sanitized fixtures and real persistence boundaries where the failure crosses transactions; no production fault injection is assumed.

## Dependencies and gates

No task dependency. Spike revision 1 and task promotion are recorded; implementation plan revision 1 is approved.

This task is promoted under spike revision 1. Implementation plan revision 1 is approved; the dependency gate must be satisfied or validly stacked before implementation.

## Rollout and automatic operation

Version request/normalizer/review policy, supersede AD-034's recurring use explicitly, and evaluate old/new decisions in observation mode before selecting corrected points. Keep existing provider quotas.

Normal successful work, contention/transient retry, and restart recovery must require no per-record owner action. Escalate only an unresolved material ambiguity, protected-value conflict, repeated systemic/access failure, or destructive recovery decision after the bounded automatic path has been exhausted.

## Rollback and recovery

Disable new selection writes and retain prior selection lineage; keep invalid results visibly uncertain rather than re-enabling blanket acceptance.

## Risks and exclusions

Owner visibility preferences behind AD-034 must be preserved through honest approximate/list discovery. No additional hosted provider or paid quota is authorized by this proposal.

Do not add production dependencies without owner approval, commit raw source/credentials, or mix unrelated refactoring into this task. General E14 infrastructure remains authoritative outside this task's specific regression/behavior scope.

## Promotion checklist

- [x] Spike revision 1 approval interpretation recorded in the owner decision.
- [ ] Scope, acceptance, dependencies, tests, risks, rollout, and rollback reviewed against that revision.
- [ ] All referenced dependencies and required decisions resolved for the planned sequence.
- [x] File moved, not copied, into `tasks/` with attributable promotion metadata.
- [ ] Dedicated branch and PR will cover this task only after implementation gates clear.

## Refined implementation boundary

Implement the corresponding T1 section of [implementation plan revision 1](../IMPLEMENTATION_PLAN.md), including its numeric budgets, migration/contract boundaries, protected-state guards and verification requirements. This refinement is task revision 2. No acceptance case is marked fixed by planning.

## Start evidence

Passed through ready with no task dependencies and approved spike 1 / plan 1 gates. Started on the dedicated T1 branch from main `4ba7e23` plus planning commit `a226bb1`. The planning branch is the documentation ancestor; it must land before this task PR.

## Implementation evidence

[T1 verification](../T1_VERIFICATION.md) maps sanitized regressions, persistence/race tests, validation commands and remaining production boundaries. T1 passed required CI, merged and released. The later [production rollout](../PRODUCTION_ROLLOUT.md) records the live outcomes: the reported cases are quarantined and discoverable; exact replacement coordinates are not claimed fixed.

## Delivery evidence

PR #355 merged as `6722ecb79d47958a92eb3608aeade1a4a3cede9e`; all required checks and [release](https://github.com/Flippylolz/WEF/actions/runs/34016504593) succeeded. This completes future-decision validation, not the existing-location repair or either owner-reported production case.
