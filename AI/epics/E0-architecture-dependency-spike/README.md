---
schema: ai-workflow/epic@1
id: E0
title: "Architecture and dependency spike"
status: ready
milestones: [M1]
owner: owner
spike: SPIKE.md
implementation_plan: IMPLEMENTATION_PLAN.md
---

# E0: Architecture and dependency spike

## Outcome

implementation starts from a reviewed backend-centric modular-monolith proof and reproducible dependency lockfiles, not ad hoc framework choices.

## Approval state

- Epic workspace status: `ready`; both approval artifacts are current, but tasks remain dependency-blocked by E1-T1.
- [Spike](SPIKE.md): `approved`, revision 2, explicitly approved by the owner, research only, no code. Revision 2 adds explicit repository, Dockerfile, Compose, Makefile, root README, task-ownership, and branch boundaries.
- [Implementation plan](IMPLEMENTATION_PLAN.md): `approved`, revision 2, with E0-T1 and E0-T2 as the only sequence entries.
- E0-T1 and E0-T2 were moved to `tasks/` after spike approval and have satisfied approval gates, but remain `draft` until E1-T1 and their remaining task gates pass.

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

- [E0-T1: Review architecture and dependency proposal](tasks/E0-T1-review-architecture-and-dependency-proposal.md) — `draft`, P0/M, M1; blocked by E1-T1 and implementation-plan approval.
- [E0-T2: Execute and lock the architecture proof](tasks/E0-T2-execute-and-lock-the-architecture-proof.md) — `draft`, P0/M, M1; blocked by E0-T1, E1-T1, and implementation-plan approval.

## Cross-epic dependencies

- Incoming: E0-T1 and E0-T2 depend on E1-T1.
- Outgoing: E1-T2 depends on E0-T2.

The exact normalized dependency and traceability registry is maintained in the [epics index](../README.md). Each workflow candidate is authoritative only in the single linked `proposed-tasks/` file above; its `legacy-roadmap:*` source value records non-path provenance.

## Lifecycle

Follow the [approval-gated workflow](../../workflow/README.md), [proposed-task schema](../../workflow/templates/PROPOSED_TASK.md), [implementation-plan schema](../../workflow/templates/IMPLEMENTATION_PLAN.md), and [definition of done](../../workflow/DEFINITION_OF_DONE.md). Priority, roadmap order, or epic selection never bypasses owner approvals, promotion, completed dependencies, or one-branch-per-task gates.
