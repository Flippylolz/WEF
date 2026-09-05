---
schema: ai-workflow/epic@1
id: E27
title: "Faster verified releases"
status: selected
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

## Proposed tasks

- [E27-T1: Measure merge-to-production time and report release outcomes](proposed-tasks/E27-T1-measure-release-and-report-outcomes.md) — P1/M; dependencies: none.
- [E27-T2: Parallelize verified work and bound the deployment lock](proposed-tasks/E27-T2-parallelize-verification-and-bound-deploy-lock.md) — P1/L; dependencies: E27-T1.
- [E27-T3: Prove the release budget and unattended recovery](proposed-tasks/E27-T3-prove-release-budget-and-unattended-recovery.md) — P1/M; dependencies: E27-T2.

Each file defines one independently reviewable change, tests, acceptance evidence, rollout, rollback, and exceptional manual handling. Dependencies are task IDs and remain enforceable at promotion.

## Automation requirement

The owner requested as little manual work as possible, with manual work only in extreme cases. Routine processing must use durable, bounded automatic recovery. Measure eligible work completed and human interventions. Do not trade correctness or source evidence for a superficially empty queue.

## Approval state

- Epic selected for documentation/research.
- [Spike](SPIKE.md) revision 1 is researched and awaiting owner approval.
- All 3 candidates remain `proposed`, `actionable: false`.
- [Implementation plan](IMPLEMENTATION_PLAN.md) is an empty draft shell until spike approval and task promotion.
- The audit request authorizes research and planning documents; it is not recorded as approval of future production changes.

## Scope and completion

Retain the backend-authoritative modular architecture, current dependency constraints, contact protections, and existing review/deployment safeguards. All task acceptance criteria and the [definition of done](../../workflow/DEFINITION_OF_DONE.md) must pass before completion.

E14 retains shared test infrastructure, general refactoring, capacity, and platform observability. E8 retains passive-event acceptance; E7-T5/E14-T9 retain backup and restore scope. No duplicate authoritative definitions are introduced.
