---
schema: ai-workflow/epic@1
id: E27
title: "Faster verified releases"
status: in_progress
milestones: [M5]
owner: owner
spike: SPIKE.md
implementation_plan: IMPLEMENTATION_PLAN.md
---

# E27: Faster verified releases

## Outcome

An ordinary merged PR automatically reaches a verified production release with visible stage timing, minimal duplicate work, safe serialized activation, and no routine second dispatch.

## Audit basis

Audit R1 measures three merged-PR releases at 9m31s, 10m36s, and 14m48s. Verification took 5m33s–7m05s while deploy jobs took 77–87 seconds; one waited 5m37s before starting. A manual duplicate took 20m31s. R2 confirms a successful verification/publish workflow can skip deployment because the SHA has no associated merged PR.

See the [5 September system audit](../../audits/2026-09-05-system-audit.md) for tests, production observations, source references, uncertainty, and the cross-epic sequence.

## Tasks

- [E27-T1: Measure merge-to-production time and report release outcomes](tasks/E27-T1-measure-release-and-report-outcomes.md) — P1/M; dependencies: none.
- [E27-T2: Parallelize verified work and bound the deployment lock](tasks/E27-T2-parallelize-verification-and-bound-deploy-lock.md) — P1/L; dependencies: E27-T1.
- [E27-T3: Prove the release budget and unattended recovery](tasks/E27-T3-prove-release-budget-and-unattended-recovery.md) — P1/M; dependencies: E27-T2.

Each file defines one independently reviewable change, tests, acceptance evidence, rollout, rollback, and exceptional manual handling. Dependencies are task IDs and remain enforceable at promotion.

## Automation requirement

The owner requested as little manual work as possible, with manual work only in extreme cases. Routine processing must use durable, bounded automatic recovery. Measure eligible work completed and human interventions. Do not trade correctness or source evidence for a superficially empty queue.

## Approval state

The [delivery proposal](DELIVERY_PROPOSAL.md) records the current workflow findings,
concrete task sequence, verification parity, lock boundary, and measurement design
for owner review following the selection of E27 on 2026-09-05.

- Spike revision 1 approved by the owner on 2026-09-05; [decision transcript](OWNER_DECISIONS.md).
- All three tasks promoted as revision-1 definitions with satisfied spike and implementation gates; T1 and T2 are done after successful automatic releases; T3 remains in progress.
- [Implementation plan revision 1](IMPLEMENTATION_PLAN.md) was approved by the owner on 2026-09-05.
- Ordered merges #324/#326/#329 were owner-authorized and completed. Current repository policy also provides standing authorization for eligible merges; acceptance gates remain required.

## Scope and completion

Retain the backend-authoritative modular architecture, current dependency constraints, contact protections, and existing review/deployment safeguards. All task acceptance criteria and the [definition of done](../../workflow/DEFINITION_OF_DONE.md) must pass before completion.

E14 retains shared test infrastructure, general refactoring, capacity, and platform observability. E8 retains passive-event acceptance; E7-T5/E14-T9 retain backup and restore scope. No duplicate authoritative definitions are introduced.

## Review and evidence

- [Planning PR #324](https://github.com/Flippylolz/WEF/pull/324).
- [T1 outcome reporting PR #326](https://github.com/Flippylolz/WEF/pull/326).
- [T2 release graph PR #329](https://github.com/Flippylolz/WEF/pull/329).
- [T1 baseline](BASELINE.md), [required-check parity](CHECK_PARITY.md), and
  [T3 acceptance evidence](ACCEPTANCE.md).

Planning, T1 and T2 are merged. [T3 PR #332](https://github.com/Flippylolz/WEF/pull/332) delivers the evidence tooling so production can supply cache measurements; T3 remains open for the real-release acceptance cohort. The epic is not complete from one release.
