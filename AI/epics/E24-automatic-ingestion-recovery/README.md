---
schema: ai-workflow/epic@1
id: E24
title: "Automatic ingestion recovery"
status: ready
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

## First implementation phase

- [E24-T1: Terminate original archive work and repair starvation](tasks/E24-T1-terminate-original-archive-work.md) — P1/L, revision 2, `done`; dependencies: none.
- [E24-T2: Make source cursors monotonic and retries fair](tasks/E24-T2-monotonic-cursors-and-fair-retries.md) — P1/L, revision 3, `done`; dependencies: E24-T1.

## Next task and remaining candidate

- [E24-T3: Recover media independently after message commit](tasks/E24-T3-recover-media-after-message-commit.md) — P1/L, revision 2, `ready`; implementation-plan revision 3 approved; dependencies: E24-T1.
- [E24-T4: Verify ingestion progress and automate recovery escalation](proposed-tasks/E24-T4-verify-progress-and-automate-recovery.md) — P1/M; dependencies: E24-T1, E24-T2, E24-T3.

Each file defines one independently reviewable change, tests, acceptance evidence,
rollout, rollback, and exceptional manual handling. The first plan sequences T1
then T2 as requested. T3 is promoted with plan revision 3 approved; T4 requires later promotion and planning;
finishing T1/T2 alone cannot close the epic.

## Automation requirement

The owner requested as little manual work as possible, with manual work only in extreme cases. Routine processing must use durable, bounded automatic recovery. Measure eligible work completed and human interventions. Do not trade correctness or source evidence for a superficially empty queue.

## Approval state

- Spike revision 2 is approved under AD-048. Completed plan revision 2 remains historical; revision 3 is approved for T3.
- T1 is done after PR #331 and its passing 15-minute production window. T2 is done after PR #334, corrections #340/#341, and a passing 900-second production window. See [production evidence](PRODUCTION_EVIDENCE.md).
- T3 is promoted as ready with its implementation gate satisfied; T4 remains proposed.
- Approval authorizes implementation and PR preparation; merge and production release remain separate.

## Scope and completion

Retain the backend-authoritative modular architecture, current dependency constraints, contact protections, and existing review/deployment safeguards. All task acceptance criteria and the [definition of done](../../workflow/DEFINITION_OF_DONE.md) must pass before completion.

E14 retains shared test infrastructure, general refactoring, capacity, and platform observability. E8 retains passive-event acceptance; E7-T5/E14-T9 retain backup and restore scope. No duplicate authoritative definitions are introduced.


## Current continuation gate

T1/T2 remain done. T3 is promoted for planning under approved spike revision 2; implementation-plan revision 3 is owner-approved. T4 remains proposed. Planning continuation does not authorize source-conflict overrides or T3 code before that approval.
