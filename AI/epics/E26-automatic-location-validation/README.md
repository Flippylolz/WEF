---
schema: ai-workflow/epic@1
id: E26
title: "Automatic location validation and repair"
status: in_progress
milestones: [M5]
owner: owner
spike: SPIKE.md
implementation_plan: IMPLEMENTATION_PLAN.md
---

# E26: Automatic location validation and repair

## Outcome

Map positions agree with source addresses and expose their true precision. Routine wrong or stale geocodes are detected, re-resolved, and corrected automatically; owner involvement is reserved for material ambiguity and protected-value conflicts.

## Audit basis

Audit M1 identifies both owner-reported cases and an additional Jugosłowiańska result whose provider address is Grochowska town hall despite confidence 1.00. Coarse pending results are automatically accepted using historical manual_accept lineage. All three selected results use v1 query/request versions. M2 also reproduces Gocław being treated as a city in display normalization.

See the [5 September system audit](../../audits/2026-09-05-system-audit.md) for tests, production observations, source references, uncertainty, and the cross-epic sequence.

## Promoted tasks

- [E26-T1: Validate address agreement and source-supported precision](tasks/E26-T1-validate-address-agreement-and-precision.md) — P1/L; dependencies: none.
- [E26-T2: Revalidate and repair existing points automatically](tasks/E26-T2-revalidate-and-repair-existing-points.md) — P1/L; dependencies: E24-T1, E26-T1.
- [E26-T3: Show honest map precision and prove real pin behavior](tasks/E26-T3-show-honest-map-precision.md) — P1/M; dependencies: E26-T1, E14-T5.

Each file defines one independently reviewable change, tests, acceptance evidence, rollout, rollback, and exceptional manual handling. Dependencies are task IDs and remain enforceable at promotion.

- [E26-T4: Municipal-first resolution](tasks/E26-T4-resolve-municipal-first.md) — P1/M; dependencies: E26-T1–T3; implementation in progress under approved revision 2.

## Automation requirement

The owner requested as little manual work as possible, with manual work only in extreme cases. Routine processing must use durable, bounded automatic recovery. Measure eligible work completed and human interventions. Do not trade correctness or source evidence for a superficially empty queue.

## Approval state

- Spike revision 1 advanced to approved from the owner's direction to start; interpretation and exact instruction are in [OWNER_DECISION.md](OWNER_DECISION.md).
- All three tasks are promoted at revision 2; implementation gates are approved.
- [Implementation plan revision 1](IMPLEMENTATION_PLAN.md) is approved by the owner; implementation proceeds task by task.
- E24-T1, the five owner-approved E14 prerequisites and all three E26 tasks are done. The rollback-compatible release preceded T2; live canary verification preceded automatic expansion.
- The original wrong pins were quarantined. On 6 September, owner-authorized municipal street-level corrections were applied and verified for Ostrzycka and both Jugosłowiańska cases. These operator selections are protected; exact buildings remain unknown. See the follow-up [municipal policy](MUNICIPAL_FIRST.md).
- The final documentation release exposed a separate browser synchronization defect; [map rendering readiness](MAP_RENDER_READINESS.md) records the follow-up correction without changing location policy.
- The remaining catalog pass is running automatically under the existing daily budget. Epic completion records deployed behavior and verified rollout, not an already-drained queue.

## Scope and completion

Retain the backend-authoritative modular architecture, current dependency constraints, contact protections, and existing review/deployment safeguards. All task acceptance criteria and the [definition of done](../../workflow/DEFINITION_OF_DONE.md) must pass before completion.

E14 retains shared test infrastructure, general refactoring, capacity, and platform observability. E8 retains passive-event acceptance; E7-T5/E14-T9 retain backup and restore scope. No duplicate authoritative definitions are introduced.
