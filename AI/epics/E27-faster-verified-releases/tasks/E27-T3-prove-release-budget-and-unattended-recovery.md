---
schema: ai-workflow/task@1
id: E27-T3
epic: E27
title: "Prove the release budget and unattended recovery"
status: deferred
revision: 1
priority: P1
size: M
milestone: M5
dependencies: [E27-T2]
requirement_ids: []
decision_ids: [ADR-008, ADR-009, ADR-010, ADR-013, ADR-014, ADR-017, ADR-023]
deferred_decision_ids: []
promotion:
  source: ../proposed-tasks/E27-T3-prove-release-budget-and-unattended-recovery.md
  promoted_by: codex
  promoted_at: "2026-09-05T10:18:07Z"
spike_gate:
  status: satisfied
  file: ../SPIKE.md
  approved_revision: 1
  verified_by: codex
  verified_at: "2026-09-05T10:18:07Z"
implementation_gate:
  status: satisfied
  file: ../IMPLEMENTATION_PLAN.md
  approved_revision: 1
  verified_by: codex
  verified_at: "2026-09-05T10:22:10Z"
dependency_gate:
  status: satisfied
  verified_by: codex
  verified_at: "2026-09-05T12:05:44+00:00"
  evidence:
    - task_id: E27-T2
      branch: chore/E27-T2-parallel-release
      pull_request: https://github.com/Flippylolz/WEF/pull/329
      head_commit: 8e3548ea0533d9d3f762ca760f74c90d70b78dde
branch:
  required: true
  name: chore/E27-T3-release-budget
  task_id: E27-T3
  one_task_only: true
  created_at: "2026-09-05T11:06:27Z"
  pull_request: https://github.com/Flippylolz/WEF/pull/332
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

# E27-T3: Prove the release budget and unattended recovery

## Outcome

Measured releases are materially faster and ordinary deployment failures either recover automatically or produce one actionable exception.

## Scope and work

Compare before/after merged-PR cohorts, establish the accepted latency budget, rehearse failure/rollback through existing controls, and document unattended operation and exceptional manual recovery.

Relevant seams are listed in the [epic spike](../SPIKE.md#research-method-and-evidence). The [audit](../../../audits/2026-09-05-system-audit.md) supplies the verified baseline and distinguishes source-confirmed risks from production observations.

## Acceptance criteria

- [ ] Proposed target, subject to the T1 baseline: merge-to-healthy p50 at most five minutes and p95 at most seven minutes over at least 20 eligible ordinary releases; report total latency including queue time and publish any unmet target transparently.
- [ ] Warm/cold dependency and image-cache cases plus queued consecutive merges are represented; provider/runner incidents are recorded separately without being silently removed from total-latency reporting.
- [ ] A failed health check restores the previous verified release automatically using existing rollback controls, and status reports the failed candidate and restored healthy SHA.
- [ ] No routine merge needs manual dispatch, SSH, configuration editing, or per-release approval; exhausted recovery, credentials/access problems, or destructive migration decisions are the defined exceptions.
- [ ] Final evidence lists required-check parity, immutable image digests, healthy version confirmation, shared-host non-interference, and operator interventions, with no sensitive configuration in artifacts.

## Tests and verification

Run existing local production proofs and controlled health/rollback failure cases; collect actual authorized deployment observations rather than generating unnecessary production deploys to fill the cohort.

Run affected format/lint/type/test/contract checks, the [definition of done](../../../workflow/DEFINITION_OF_DONE.md), and `make lint` / `make test` before a push. Record exact commands and outcomes in the task PR. Use synthetic/sanitized fixtures and real persistence boundaries where the failure crosses transactions; no production fault injection is assumed.

## Dependencies and gates

Required task dependencies: E27-T2. Their completed or valid stacked state must be proven before implementation begins; all must be done before completion/merge.

This task is `deferred` at the owner’s request; its T2 dependency is done. The [implementation plan](../IMPLEMENTATION_PLAN.md) specifies modules, contracts, tests, budgets, and rollout.

## Rollout and automatic operation

Observe real normal releases after T2. If the budget is missed, use measured stage/queue data to choose the next bounded optimization rather than weakening gates.

Normal successful work, contention/transient retry, and restart recovery must require no per-record owner action. Escalate only an unresolved material ambiguity, protected-value conflict, repeated systemic/access failure, or destructive recovery decision after the bounded automatic path has been exhausted.

## Rollback and recovery

Restore the prior verified workflow path on safety regression; preserve measurements and incident evidence. Existing backup deferral still limits destructive data recovery.

## Risks and exclusions

Twenty real releases may take time. Do not mark this task done from a small illustrative sample or an estimated speedup.

Do not add production dependencies without owner approval, commit raw source/credentials, or mix unrelated refactoring into this task. General E14 infrastructure remains authoritative outside this task's specific regression/behavior scope.

## Promotion checklist

- [x] Current epic spike revision explicitly approved.
- [x] Scope, acceptance, dependencies, tests, risks, rollout, and rollback reviewed against that revision.
- [x] Required decisions resolved; dependencies remain enforceable in the planned sequence.
- [x] File moved, not copied, into `tasks/` with attributable promotion metadata.
- [x] Dedicated branch covers this task under the validated stacked gate; PR evidence follows.

Start evidence: passed through `ready` after verifying open ancestor PR #329 at
`2362894f12328bfc1145da397ab7f026cf1ff474`, then entered `in_progress` on its
dedicated branch. Operational performance acceptance remains open.

Implementation evidence: [acceptance record](../ACCEPTANCE.md) documents the
read-only collector, cache telemetry, passing local checks and remaining real
release cohort. None of the unchecked operational acceptance criteria is waived.

Dependency revalidation: T2 merged and its automatic release 33964655697 passed.
PR #332 is rebased onto current main and delivers the measurement tooling. The first optimized
observation is 348.379957 seconds, with `insufficient_observations` (1 of 20
required distinct sources). Production cache counters, cold/warm coverage,
consecutive-merge evidence and cohort acceptance remain open; no completion is
claimed from this rollout.

## Instrumentation rollout versus task completion

Ship the validated measurement code in PR #332 so ordinary releases can produce
cache counters. Keep this task `in_progress` and its completion fields unset
until the real cohort and all operational criteria pass. The approved plan says
"Insufficient data keeps performance acceptance open"; it does not require
withholding the instrumentation needed to collect that data. The earlier draft
hold was an implementation sequencing choice, not an additional owner gate.
This rollout changes no target, minimum sample, required check or acceptance
criterion. Continue collecting ordinary releases; do not generate a synthetic
production cohort. Record final acceptance through a separately scoped evidence
follow-up after the observations exist, without reusing the merged code branch.

## Owner-directed deferral

The owner requested "merge evidence and we can close this for now" on 2026-09-05.
The [evidence closeout](../EVIDENCE_CLOSEOUT.md) records six ordinary releases,
working production cache counters and isolated local cold/warm proofs. Final
acceptance is deferred, not passed; completion metadata remains unset.
The named resumption trigger is the owner reopening E27 to gather at least
20 eligible observed releases plus the remaining production cache/queue and
incident/intervention evidence. Use a new branch and revalidate gates then.
This disposition supersedes earlier ongoing-work statements above without
changing the original acceptance thresholds or claiming task completion.
