---
schema: ai-workflow/task@1
id: E27-T2
epic: E27
title: "Parallelize verified work and bound the deployment lock"
status: done
revision: 1
priority: P1
size: L
milestone: M5
dependencies: [E27-T1]
requirement_ids: []
decision_ids: [ADR-008, ADR-009, ADR-010, ADR-013, ADR-014, ADR-017, ADR-023]
deferred_decision_ids: []
promotion:
  source: ../proposed-tasks/E27-T2-parallelize-verification-and-bound-deploy-lock.md
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
  verified_at: "2026-09-05T11:47:14+00:00"
  evidence:
    - task_id: E27-T1
      branch: chore/E27-T1-release-outcomes
      pull_request: https://github.com/Flippylolz/WEF/pull/326
      head_commit: 1700f0491ad8d40c0c2fd8e822b7341f472dba91
branch:
  required: true
  name: chore/E27-T2-parallel-release
  task_id: E27-T2
  one_task_only: true
  created_at: "2026-09-05T10:54:53Z"
  pull_request: https://github.com/Flippylolz/WEF/pull/329
completion:
  completed_by: codex
  completed_at: "2026-09-05T12:05:44+00:00"
  pull_request: https://github.com/Flippylolz/WEF/pull/329
  evidence:
    - ../CHECK_PARITY.md
    - ../ACCEPTANCE.md
    - https://github.com/Flippylolz/WEF/actions/runs/33964655697
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# E27-T2: Parallelize verified work and bound the deployment lock

## Outcome

Release verification and image preparation do independent work concurrently while production mutations remain serialized and tied to one verified immutable SHA.

## Scope and work

Consolidate equivalent CI/release checks using reusable repository-owned definitions, remove redundant host/Compose setup where parity is proven, parallelize backend/frontend and image work, retain cache scopes, and narrow concurrency to activation with stale-candidate protection.

Relevant seams are listed in the [epic spike](../SPIKE.md#research-method-and-evidence). The [audit](../../../audits/2026-09-05-system-audit.md) supplies the verified baseline and distinguishes source-confirmed risks from production observations.

## Acceptance criteria

- [x] A check-parity matrix proves all existing required lint/type/test/contract/script/topology/security/image validations remain represented for the exact release SHA; missing/cancelled/failing evidence cannot deploy.
- [x] Backend/frontend checks and backend/web image builds can run independently; locked dependencies and one deliberate disposable PostGIS test setup replace redundant installs/databases where appropriate.
- [x] Production configuration transfer, migration, activation, health verification, and rollback share a serialization boundary; an older queued candidate cannot overwrite a newer healthy release.
- [x] An eligible merged PR automatically deploys after checks. Repeated requests for an already verified/deployed SHA reuse or no-op only with digest/source/gate evidence, and never execute concurrent activation.
- [x] PR/fork runs receive no production secrets or write-scoped release execution; immutable SHA/digest identity, associated-PR enforcement, shared-host isolation, and rollback proofs remain intact.

## Tests and verification

Update prove_release_workflow and deploy-gate tests with an explicit job/dependency matrix, stale release ordering, duplicate dispatch, failed check, missing artifact, wrong SHA/digest, and activation/rollback concurrency cases.

Run affected format/lint/type/test/contract checks, the [definition of done](../../../workflow/DEFINITION_OF_DONE.md), and `make lint` / `make test` before a push. Record exact commands and outcomes in the task PR. Use synthetic/sanitized fixtures and real persistence boundaries where the failure crosses transactions; no production fault injection is assumed.

## Dependencies and gates

Required task dependencies: E27-T1. Their completed or valid stacked state must be proven before implementation begins; all must be done before completion/merge.

This task is `done`; its initially stacked dependency is satisfied. The [implementation plan](../IMPLEMENTATION_PLAN.md) specifies the modules, contracts, tests, budgets, and rollout for this task.

## Rollout and automatic operation

Split execution in reviewable stages behind unchanged deployment safety gates. Compare baseline timings before switching the production lock scope; retain an exact-SHA manual emergency path.

Normal successful work, contention/transient retry, and restart recovery must require no per-record owner action. Escalate only an unresolved material ambiguity, protected-value conflict, repeated systemic/access failure, or destructive recovery decision after the bounded automatic path has been exhausted.

## Rollback and recovery

Restore the previous workflow ordering if concurrency or parity fails; do not roll back production data or cancel an activation in the middle of migration.

## Risks and exclusions

Do not trust PR-head success as merge-SHA success. Avoid an optimization that runs untrusted workflow_run artifacts with production credentials. No new runner/service/dependency is pre-approved.

Do not add production dependencies without owner approval, commit raw source/credentials, or mix unrelated refactoring into this task. General E14 infrastructure remains authoritative outside this task's specific regression/behavior scope.

## Promotion checklist

- [x] Current epic spike revision explicitly approved.
- [x] Scope, acceptance, dependencies, tests, risks, rollout, and rollback reviewed against that revision.
- [x] Required decisions resolved; dependencies remain enforceable in the planned sequence.
- [x] File moved, not copied, into `tasks/` with attributable promotion metadata.
- [x] Dedicated branch covers this task after implementation and stacked dependency gates cleared.

Start evidence: passed through `ready` after verifying open ancestor PR #326 at
`f81fb7c10bd1800a059240c464d955e89622b840`; then entered `in_progress` on its
dedicated branch. Completion awaits the dependency and production evidence.

## Implementation evidence (pending PR and production acceptance)

[Check parity](../CHECK_PARITY.md) records the complete CI/release check union and
permission boundaries. Shared exact-SHA verification, parallel inspected image
builds, validated artifact reuse, full-job production concurrency, source-ancestry
ordering, host-locked state guards and duplicate health/configuration proofs are
implemented. Run-attempt observations remain truthful when verification is reused.

Local validation passed: 803 backend tests, 169 frontend tests, release report and
ordering tests, CI-equivalent script format/lint/strict types, workflow/composite
shell checks, production/rollback/shared-edge proofs, runtime image builds and
production runtime/persistence proof. Production acceptance remains pending the
normal release after an owner-authorized merge. T1 remains the open ancestor PR.

Merge dependency revalidation: T1 is done after PR #326 and its successful
normal release run 33963661845. T2 was rebased onto the resulting main commit;
local lint, 803 backend tests, 169 frontend tests, production/rollback/shared-edge
proofs passed again. Required PR checks must pass on this final head before merge.

Completion: PR #329 merged as `8e3548ea0533d9d3f762ca760f74c90d70b78dde`
after all nine visible CI checks passed on the latest-main head. Automatic release
33964655697 passed all verification, exact-digest runtime, artifact validation,
health, activation and shared-host checks. Its report confirms `deployed`, healthy
source `8e3548ea0533d9d3f762ca760f74c90d70b78dde`, host health at
2026-09-05T12:02:09.379957Z, and activation at 12:02:09.477130Z. Public HTTPS
independently showed version `8e3548e` and readiness `ready`. The local/public
release-header distinction did not affect deployment: the public edge exposes
the HTML version marker, while the internal smoke checks the release header.

Five independent preparation jobs began within two seconds. No operator dispatch,
SSH, configuration edit or extra approval was needed. Local held-lock, stale-SHA,
same-SHA, missing/expired/foreign evidence, interrupted-mutation and rollback
proofs cover the guarded failure paths without production fault injection.
Merge-to-observed-health was 348.379957 seconds; T3 owns the still-incomplete
20-release latency/cache/consecutive-merge acceptance.
