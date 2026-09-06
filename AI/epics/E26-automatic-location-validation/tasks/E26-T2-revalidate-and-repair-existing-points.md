---
schema: ai-workflow/task@1
id: E26-T2
epic: E26
title: "Revalidate and repair existing points automatically"
status: in_progress
revision: 2
priority: P1
size: L
milestone: M5
dependencies: [E24-T1, E26-T1]
requirement_ids: [P-001, P-003, P-004, P-007]
decision_ids: [ADR-003, ADR-005, ADR-012, ADR-021]
deferred_decision_ids: []
source: "owner-requested-system-audit:2026-09-05"
promotion:
  source: ../proposed-tasks/E26-T2-revalidate-and-repair-existing-points.md
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
  evidence: ["E24-T1 done via PR #331", "E26-T1 done via PR #355, merge 6722ecb79d47958a92eb3608aeade1a4a3cede9e; release 34016504593 succeeded"]
branch:
  required: true
  name: feat/E26-T2-location-revalidation
  task_id: E26-T2
  one_task_only: true
  created_at: "2026-09-06T05:55:31Z"
  pull_request: https://github.com/Flippylolz/WEF/pull/357
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

This task is promoted under spike revision 1. Implementation plan revision 1 is approved; the dependency gate must be satisfied or validly stacked before implementation.

## Rollout and automatic operation

Run after E24-T1 so repair does not compete with archive starvation. Canary known regression cases and a stratified set including high-confidence points, then expand within durable daily budgets.

Normal successful work, contention/transient retry, and restart recovery must require no per-record owner action. Escalate only an unresolved material ambiguity, protected-value conflict, repeated systemic/access failure, or destructive recovery decision after the bounded automatic path has been exhausted.

## Rollback and recovery

Pause scheduling and revert only unchanged automatically selected points through their recorded predecessor selection. Keep invalidated results quarantined from precise display.

## Risks and exclusions

Coarse-point counts overlap low confidence and missing districts; do not size repair or claim accuracy improvement by adding those overlapping populations.

Do not add production dependencies without owner approval, commit raw source/credentials, or mix unrelated refactoring into this task. General E14 infrastructure remains authoritative outside this task's specific regression/behavior scope.

## Promotion checklist

- [x] Spike revision 1 approval interpretation recorded in the owner decision.
- [ ] Scope, acceptance, dependencies, tests, risks, rollout, and rollback reviewed against that revision.
- [ ] All referenced dependencies and required decisions resolved for the planned sequence.
- [x] File moved, not copied, into `tasks/` with attributable promotion metadata.
- [ ] Dedicated branch and PR will cover this task only after implementation gates clear.

## Refined implementation boundary

Implement the corresponding T2 section of [implementation plan revision 1](../IMPLEMENTATION_PLAN.md), including its numeric budgets, migration/contract boundaries, protected-state guards and verification requirements. This refinement is task revision 2. No acceptance case is marked fixed by planning.

## Start evidence

Passed through ready under the approved plan with E24-T1 done and E26-T1 on ancestor PR #355. Started on the dedicated T2 worktree; no merge/completion until dependency gates are satisfied. Existing-location application and production acceptance remain gated by T3 discovery and the canary requirements.

## Implementation evidence

See [T2_VERIFICATION.md](../T2_VERIFICATION.md) for implemented guards, test
scope and outstanding release/canary acceptance. The implementation PR remains
draft while these acceptance gates are open. Existing production examples remain
unverified; test fixtures are synthetic.
