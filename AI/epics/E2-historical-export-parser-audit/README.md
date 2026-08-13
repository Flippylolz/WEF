---
schema: ai-workflow/epic@1
id: E2
title: "Historical export parser and audit"
status: ready
milestones: [M1, M2]
owner: owner
spike: SPIKE.md
implementation_plan: IMPLEMENTATION_PLAN.md
---

# E2: Historical export parser and audit

## Outcome

deterministic extraction from the raw Telegram export with reconciled dry-run reporting.

## Approval state

- Epic workspace status: `ready`.
- [Spike](SPIKE.md): `approved`, revision 2, owner-approved research; it permits promotion/planning only, no code.
- [Implementation plan](IMPLEMENTATION_PLAN.md): `approved`, revision 2, sequencing promoted E2-T1 only.
- E2-T1 is promoted/`done` through [PR #33](https://github.com/Flippylolz/WEF/pull/33), with aggregate-only source acceptance and required CI evidence.
- Every remaining file in `proposed-tasks/` is non-actionable.

## Milestones

[M1](../../milestones/M1-vertical-proof.md), [M2](../../milestones/M2-historical-dataset-ready.md)

## Governing domain documents

- [Data](../../data/README.md)
- [Ingestion](../../ingestion/README.md)
- [Contracts](../../contracts/README.md)
- [Security](../../security/README.md)
- [Decisions](../../decisions/README.md)

## Governing decisions and deferred gates

- [ADR-003](../../decisions/adr/ADR-003-do-not-infer-current-availability.md)
- [ADR-006](../../decisions/adr/ADR-006-shared-ingestion-core.md)
- [ADR-007](../../decisions/adr/ADR-007-mounted-media-storage-interface.md)
- [ADR-012](../../decisions/adr/ADR-012-backend-centric-modular-monolith.md)

## Promoted task

- [E2-T1: Implement source adapter and fixture corpus](tasks/E2-T1-implement-source-adapter-and-fixture-corpus.md) — `done`, P0/M, M1

## Proposed tasks

- [E2-T2: Implement candidate detection and typed extractors](proposed-tasks/E2-T2-implement-candidate-detection-and-typed-extractors.md) — `proposed`, P0/L, M1
- [E2-T3: Implement media grouping](proposed-tasks/E2-T3-implement-media-grouping.md) — `proposed`, P0/M, M2
- [E2-T4: Implement dry-run reports](proposed-tasks/E2-T4-implement-dry-run-reports.md) — `proposed`, P0/M, M2
- [E2-T5: Audit the complete export](proposed-tasks/E2-T5-audit-the-complete-export.md) — `proposed`, P0/L, M2

## Cross-epic dependencies

- Incoming: E2-T1 depends on E1-T2.
- Outgoing: E3-T2 depends on E2-T2.
- Outgoing: E3-T3 depends on E2-T2.
- Outgoing: E3-T4 depends on E2-T3.
- Outgoing: E3-T5 depends on E2-T5.
- Outgoing: E6-T5 depends on E2-T2.

The exact normalized dependency and traceability registry is maintained in the [epics index](../README.md). Each workflow candidate is authoritative only in the single linked `proposed-tasks/` file above; its `legacy-roadmap:*` source value records non-path provenance.

## Lifecycle

Follow the [approval-gated workflow](../../workflow/README.md), [proposed-task schema](../../workflow/templates/PROPOSED_TASK.md), [implementation-plan schema](../../workflow/templates/IMPLEMENTATION_PLAN.md), and [definition of done](../../workflow/DEFINITION_OF_DONE.md). Priority, roadmap order, or epic selection never bypasses owner approvals, promotion, completed dependencies, or one-branch-per-task gates.
