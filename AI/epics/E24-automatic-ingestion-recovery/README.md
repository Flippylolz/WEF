---
schema: ai-workflow/epic@1
id: E24
title: "Automatic ingestion recovery"
status: in_progress
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

## Active acceptance work

- [E24-T3: Recover media independently after message commit](tasks/E24-T3-recover-media-after-message-commit.md) — deployed through PR #346; `in_progress` because actual production derivative-repair evidence remains open.
- [E24-T4: Verify ingestion progress and automate recovery escalation](tasks/E24-T4-verify-progress-and-automate-recovery.md) — revision 2, `in_progress` through PR #354; implementation-plan revision 4 is approved. Dependencies T1/T2 are done; deployed T3 interfaces are verified under the owner-approved sequencing change.

Historical media discovery is drained. At 2026-09-06T05:26Z, 22,266 assets were
completed, 3,480 quarantined and 2,356 unsupported, with no pending intentions or
work. No new variants were generated, so this does not close T3 acceptance.

## Automation requirement

The owner requested as little manual work as possible, with manual work only in extreme cases. Routine processing must use durable, bounded automatic recovery. Measure eligible work completed and human interventions. Do not trade correctness or source evidence for a superficially empty queue.

## Approval state

- Spike revision 2 and implementation-plan revision 4 are owner-approved. Earlier approved revisions remain historical evidence.
- T1 and T2 are done; see [production evidence](PRODUCTION_EVIDENCE.md).
- T3 remains open for actual repair evidence. The owner explicitly allowed T4 implementation against its deployed interfaces without waiting for that separate acceptance gate.
- T4 has merged through green CI and remains in progress until its production rollout and full 24-hour acceptance are verified. No separate per-PR merge confirmation is required.

## Scope and completion

Retain the backend-authoritative modular architecture, current dependency constraints, contact protections, and existing review/deployment safeguards. All task acceptance criteria and the [definition of done](../../workflow/DEFINITION_OF_DONE.md) must pass before completion.

E14 retains shared test infrastructure, general refactoring, capacity, and platform observability. E8 retains passive-event acceptance; E7-T5/E14-T9 retain backup and restore scope. No duplicate authoritative definitions are introduced.


## Current continuation gate

T4 starts with observation-only samples, then a healthy 15-minute window permits
incident activation. A full 24-hour runtime window and reviewed absence of routine
operator interventions are required before T4 completion. T3's actual production
repair gate remains independent; neither task's deployment alone closes E24.
