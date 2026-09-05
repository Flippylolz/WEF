---
schema: ai-workflow/epic@1
id: E24
title: "Automatic ingestion recovery"
status: selected
milestones: [M5]
owner: owner
spike: SPIKE.md
implementation_plan: IMPLEMENTATION_PLAN.md
---

# E24: Automatic ingestion recovery

## Outcome

New, edited, and deleted source messages converge into the catalog with durable archive and media completion. Routine contention, restarts, and transient failures recover automatically, and health measures progress rather than repeated work.

## Audit basis

Audit I1 confirms a replay identity mismatch: 27,656 eligible pending rows, 25 pending rows with alternate-checksum terminal siblings, and sampled copies processed over 20,000 times. I2 records inconsistent durable/runtime cursors and lock-contention failures. I3 identifies a media retry gap after canonical commit. Production containers were healthy despite this evidence.

See the [5 September system audit](../../audits/2026-09-05-system-audit.md) for tests, production observations, source references, uncertainty, and the cross-epic sequence.

## Proposed tasks

- [E24-T1: Terminate original archive work and repair starvation](proposed-tasks/E24-T1-terminate-original-archive-work.md) — P1/L; dependencies: none.
- [E24-T2: Make source cursors monotonic and retries fair](proposed-tasks/E24-T2-monotonic-cursors-and-fair-retries.md) — P1/L; dependencies: E24-T1.
- [E24-T3: Recover media independently after message commit](proposed-tasks/E24-T3-recover-media-after-message-commit.md) — P1/L; dependencies: E24-T1.
- [E24-T4: Verify ingestion progress and automate recovery escalation](proposed-tasks/E24-T4-verify-progress-and-automate-recovery.md) — P1/M; dependencies: E24-T1, E24-T2, E24-T3.

Each file defines one independently reviewable change, tests, acceptance evidence, rollout, rollback, and exceptional manual handling. Dependencies are task IDs and remain enforceable at promotion.

## Automation requirement

The owner requested as little manual work as possible, with manual work only in extreme cases. Routine processing must use durable, bounded automatic recovery. Measure eligible work completed and human interventions. Do not trade correctness or source evidence for a superficially empty queue.

## Approval state

- Epic selected for documentation/research.
- [Spike](SPIKE.md) revision 1 is researched and awaiting owner approval.
- All 4 candidates remain `proposed`, `actionable: false`.
- [Implementation plan](IMPLEMENTATION_PLAN.md) is an empty draft shell until spike approval and task promotion.
- The audit request authorizes research and planning documents; it is not recorded as approval of future production changes.

## Scope and completion

Retain the backend-authoritative modular architecture, current dependency constraints, contact protections, and existing review/deployment safeguards. All task acceptance criteria and the [definition of done](../../workflow/DEFINITION_OF_DONE.md) must pass before completion.

E14 retains shared test infrastructure, general refactoring, capacity, and platform observability. E8 retains passive-event acceptance; E7-T5/E14-T9 retain backup and restore scope. No duplicate authoritative definitions are introduced.
