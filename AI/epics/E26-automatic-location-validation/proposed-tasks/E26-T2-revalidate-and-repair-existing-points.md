---
schema: ai-workflow/proposed-task@1
id: E26-T2
epic: E26
title: "Revalidate and repair existing points automatically"
status: proposed
revision: 1
actionable: false
priority: P1
size: L
milestone: M5
dependencies: [E24-T1, E26-T1]
requirement_ids: [P-001, P-003, P-004, P-007]
decision_ids: [ADR-003, ADR-005, ADR-012, ADR-021]
deferred_decision_ids: []
source: "owner-requested-system-audit:2026-09-05"
promotion:
  status: not_promoted
  target: null
  promoted_by: null
  promoted_at: null
---

# E26-T2: Revalidate and repair existing points automatically

## Outcome

Already accepted stale or mismatched points converge to the current validation policy without a location-by-location operator campaign.

## Scope and work

Create a resumable candidate queue covering old policy/query versions, weak precision, mismatching address evidence, and sampled high-confidence points; automatically rank, re-resolve, and apply safe corrections with before/after lineage.

Relevant seams are listed in the [epic spike](../SPIKE.md#research-method-and-evidence). The [audit](../../../audits/2026-09-05-system-audit.md) supplies the verified baseline and distinguishes source-confirmed risks from production observations.

## Acceptance criteria

- [ ] The queue includes accepted old-version results, not only ungeocoded rows; changing a normalizer/review version schedules eligible revalidation automatically.
- [ ] The two owner examples and the town-hall mismatch are tracked to explicit outcomes. Ostrzycka is checked against authoritative street geometry; no exact replacement coordinate is invented without source evidence.
- [ ] Unambiguous corrections apply automatically with revision/owner-verification guards; source-limited cases remain approximate and irreducible conflicts create rare actionable exceptions.
- [ ] Rate limits, transient failures, restarts, and concurrent owner edits pause/defer safely and resume automatically; current valid cache evidence is reused without preventing necessary version invalidation.
- [ ] An aggregate before/after audit reports street agreement, precision distribution, affected visible offers, preserved IDs/favorites, exception reasons, and human interventions. Re-running the same version is a no-op.

## Tests and verification

Database integration tests cover accepted v1 points, wrong high-confidence matches, protected owner corrections, automatic repair races, no-result/quota handling, and deterministic checkpointed replay.

Run affected format/lint/type/test/contract checks, the [definition of done](../../../workflow/DEFINITION_OF_DONE.md), and `make lint` / `make test` before a push. Record exact commands and outcomes in the task PR. Use synthetic/sanitized fixtures and real persistence boundaries where the failure crosses transactions; no production fault injection is assumed.

## Dependencies and gates

Required task dependencies: E24-T1, E26-T1. Their completed or valid stacked state must be proven before implementation begins; all must be done before completion/merge.

This candidate remains non-actionable under the [workflow](../../../workflow/README.md). It must move rather than copy to `tasks/`, retain its ID, and receive complete promotion and gate metadata.

## Rollout and automatic operation

Run after E24-T1 so repair does not compete with archive starvation. Canary known regression cases and a stratified set including high-confidence points, then expand within durable daily budgets.

Normal successful work, contention/transient retry, and restart recovery must require no per-record owner action. Escalate only an unresolved material ambiguity, protected-value conflict, repeated systemic/access failure, or destructive recovery decision after the bounded automatic path has been exhausted.

## Rollback and recovery

Pause scheduling and revert only unchanged automatically selected points through their recorded predecessor selection. Keep invalidated results quarantined from precise display.

## Risks and exclusions

Coarse-point counts overlap low confidence and missing districts; do not size repair or claim accuracy improvement by adding those overlapping populations.

Do not add production dependencies without owner approval, commit raw source/credentials, or mix unrelated refactoring into this task. General E14 infrastructure remains authoritative outside this task's specific regression/behavior scope.

## Promotion checklist

- [ ] Current epic spike revision explicitly approved.
- [ ] Scope, acceptance, dependencies, tests, risks, rollout, and rollback reviewed against that revision.
- [ ] All referenced dependencies and required decisions resolved for the planned sequence.
- [ ] File moved, not copied, into `tasks/` with attributable promotion metadata.
- [ ] Dedicated branch and PR will cover this task only after implementation gates clear.
