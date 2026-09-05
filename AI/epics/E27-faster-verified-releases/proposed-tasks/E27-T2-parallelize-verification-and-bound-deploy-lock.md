---
schema: ai-workflow/proposed-task@1
id: E27-T2
epic: E27
title: "Parallelize verified work and bound the deployment lock"
status: proposed
revision: 1
actionable: false
priority: P1
size: L
milestone: M5
dependencies: [E27-T1]
requirement_ids: []
decision_ids: [ADR-008, ADR-009, ADR-010, ADR-013, ADR-014, ADR-017, ADR-023]
deferred_decision_ids: []
source: "owner-requested-system-audit:2026-09-05"
promotion:
  status: not_promoted
  target: null
  promoted_by: null
  promoted_at: null
---

# E27-T2: Parallelize verified work and bound the deployment lock

## Outcome

Release verification and image preparation do independent work concurrently while production mutations remain serialized and tied to one verified immutable SHA.

## Scope and work

Consolidate equivalent CI/release checks using reusable repository-owned definitions, remove redundant host/Compose setup where parity is proven, parallelize backend/frontend and image work, retain cache scopes, and narrow concurrency to activation with stale-candidate protection.

Relevant seams are listed in the [epic spike](../SPIKE.md#research-method-and-evidence). The [audit](../../../audits/2026-09-05-system-audit.md) supplies the verified baseline and distinguishes source-confirmed risks from production observations.

## Acceptance criteria

- [ ] A check-parity matrix proves all existing required lint/type/test/contract/script/topology/security/image validations remain represented for the exact release SHA; missing/cancelled/failing evidence cannot deploy.
- [ ] Backend/frontend checks and backend/web image builds can run independently; locked dependencies and one deliberate disposable PostGIS test setup replace redundant installs/databases where appropriate.
- [ ] Production configuration transfer, migration, activation, health verification, and rollback share a serialization boundary; an older queued candidate cannot overwrite a newer healthy release.
- [ ] An eligible merged PR automatically deploys after checks. Repeated requests for an already verified/deployed SHA reuse or no-op only with digest/source/gate evidence, and never execute concurrent activation.
- [ ] PR/fork runs receive no production secrets or write-scoped release execution; immutable SHA/digest identity, associated-PR enforcement, shared-host isolation, and rollback proofs remain intact.

## Tests and verification

Update prove_release_workflow and deploy-gate tests with an explicit job/dependency matrix, stale release ordering, duplicate dispatch, failed check, missing artifact, wrong SHA/digest, and activation/rollback concurrency cases.

Run affected format/lint/type/test/contract checks, the [definition of done](../../../workflow/DEFINITION_OF_DONE.md), and `make lint` / `make test` before a push. Record exact commands and outcomes in the task PR. Use synthetic/sanitized fixtures and real persistence boundaries where the failure crosses transactions; no production fault injection is assumed.

## Dependencies and gates

Required task dependencies: E27-T1. Their completed or valid stacked state must be proven before implementation begins; all must be done before completion/merge.

This candidate remains non-actionable under the [workflow](../../../workflow/README.md). It must move rather than copy to `tasks/`, retain its ID, and receive complete promotion and gate metadata.

## Rollout and automatic operation

Split execution in reviewable stages behind unchanged deployment safety gates. Compare baseline timings before switching the production lock scope; retain an exact-SHA manual emergency path.

Normal successful work, contention/transient retry, and restart recovery must require no per-record owner action. Escalate only an unresolved material ambiguity, protected-value conflict, repeated systemic/access failure, or destructive recovery decision after the bounded automatic path has been exhausted.

## Rollback and recovery

Restore the previous workflow ordering if concurrency or parity fails; do not roll back production data or cancel an activation in the middle of migration.

## Risks and exclusions

Do not trust PR-head success as merge-SHA success. Avoid an optimization that runs untrusted workflow_run artifacts with production credentials. No new runner/service/dependency is pre-approved.

Do not add production dependencies without owner approval, commit raw source/credentials, or mix unrelated refactoring into this task. General E14 infrastructure remains authoritative outside this task's specific regression/behavior scope.

## Promotion checklist

- [ ] Current epic spike revision explicitly approved.
- [ ] Scope, acceptance, dependencies, tests, risks, rollout, and rollback reviewed against that revision.
- [ ] All referenced dependencies and required decisions resolved for the planned sequence.
- [ ] File moved, not copied, into `tasks/` with attributable promotion metadata.
- [ ] Dedicated branch and PR will cover this task only after implementation gates clear.
