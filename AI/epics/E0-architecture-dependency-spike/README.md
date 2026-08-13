---
schema: ai-workflow/epic@1
id: E0
title: "Architecture and dependency spike"
status: done
milestones: [M1]
owner: owner
spike: SPIKE.md
implementation_plan: IMPLEMENTATION_PLAN.md
---

# E0: Architecture and dependency spike

## Outcome

implementation starts from a reviewed backend-centric modular-monolith proof and reproducible dependency lockfiles, not ad hoc framework choices.

## Approval state

- Epic workspace status: `done`; the approved review and architecture proof are merged with reconciled completion evidence.
- [Spike](SPIKE.md): `approved`, revision 2, explicitly approved by the owner, research only, no code. Revision 2 adds explicit repository, Dockerfile, Compose, Makefile, root README, task-ownership, and branch boundaries.
- [Implementation plan](IMPLEMENTATION_PLAN.md): `approved`, revision 3, with E0-T1 and E0-T2 as the only sequence entries and ADR-018 stacked sequencing.
- [Proof report](PROOF_REPORT.md): measured E0-T2 dependency, architecture, OpenAPI, test, advisory, and image evidence.
- E0-T1 and E0-T2 are `done`; their formerly stacked dependencies are satisfied.

## Milestones

[M1](../../milestones/M1-vertical-proof.md)

## Governing domain documents

- [Architecture](../../architecture/README.md)
- [Contracts](../../contracts/README.md)
- [Governance](../../governance/README.md)
- [Decisions](../../decisions/README.md)

## Governing decisions and deferred gates

- [ADR-001](../../decisions/adr/ADR-001-split-python-api-typescript-web.md)
- [ADR-005](../../decisions/adr/ADR-005-postgresql-postgis.md)
- [ADR-012](../../decisions/adr/ADR-012-backend-centric-modular-monolith.md)
- [ADR-013](../../decisions/adr/ADR-013-committed-openapi-offline-docs.md)

## Promoted tasks

- [E0-T1: Review architecture and dependency proposal](tasks/E0-T1-review-architecture-and-dependency-proposal.md) — `done`, revision 2, P0/M, M1.
- [E0-T2: Execute and lock the architecture proof](tasks/E0-T2-execute-and-lock-the-architecture-proof.md) — `done`, revision 2, P0/M, M1.

## Cross-epic dependencies

- Incoming: E0-T1 and E0-T2 depend on E1-T1.
- Outgoing: E1-T2 depends on E0-T2.

The exact normalized dependency and traceability registry is maintained in the [epics index](../README.md). Each workflow candidate is authoritative only in the single linked `proposed-tasks/` file above; its `legacy-roadmap:*` source value records non-path provenance.

## Lifecycle

Follow the [approval-gated workflow](../../workflow/README.md), [proposed-task schema](../../workflow/templates/PROPOSED_TASK.md), [implementation-plan schema](../../workflow/templates/IMPLEMENTATION_PLAN.md), and [definition of done](../../workflow/DEFINITION_OF_DONE.md). Priority, roadmap order, or epic selection never bypasses owner approvals, promotion, completed dependencies, or one-branch-per-task gates.
