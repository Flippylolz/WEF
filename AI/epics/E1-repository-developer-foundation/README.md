---
schema: ai-workflow/epic@1
id: E1
title: "Repository and developer foundation"
status: in_progress
milestones: [M1]
owner: owner
spike: SPIKE.md
implementation_plan: IMPLEMENTATION_PLAN.md
---

# E1: Repository and developer foundation

## Outcome

a reproducible monorepo that cannot accidentally commit or package the source archive/media.

## Approval state

- Epic workspace status: `in_progress`; revision 4 foundation tasks and revision 5 Dependabot configuration are `done`; E1-T7 remains proposed.
- [Spike](SPIKE.md): `approved`, revision 2, explicitly approved by the owner, research only, no code. It defines separate ownership and branches for repository safety, application Dockerfiles/Make targets, and local Compose.
- [Implementation plan](IMPLEMENTATION_PLAN.md): `approved`, revision 5, authorizing E1-T6 only (Dependabot update PRs).
- E1-T1, E1-T2, E1-T4, E1-T3, and E1-T6 are `done`.
- E1-T5 remains cancelled; E1-T7 remains non-actionable under `proposed-tasks/`.

## Milestones

[M1](../../milestones/M1-vertical-proof.md)

## Governing domain documents

- [Architecture](../../architecture/README.md)
- [Governance](../../governance/README.md)
- [Operations](../../operations/README.md)
- [Decisions](../../decisions/README.md)

## Governing decisions and deferred gates

- [ADR-001](../../decisions/adr/ADR-001-split-python-api-typescript-web.md)
- [ADR-005](../../decisions/adr/ADR-005-postgresql-postgis.md)
- [ADR-008](../../decisions/adr/ADR-008-single-server-immutable-deployments.md)
- [ADR-009](../../decisions/adr/ADR-009-feature-branch-development.md)
- [ADR-010](../../decisions/adr/ADR-010-isolate-wef-shared-nuc.md)
- [ADR-012](../../decisions/adr/ADR-012-backend-centric-modular-monolith.md)
- [ADR-013](../../decisions/adr/ADR-013-committed-openapi-offline-docs.md)
- [ADR-017](../../decisions/adr/ADR-017-no-enforced-branch-protection.md)
- [D-007](../../decisions/deferred/D-007-github-protection-eligibility.md)

## Tasks

- [E1-T1: Initialize repository safety](tasks/E1-T1-initialize-repository-safety.md) — promoted, `done`, P0/S, M1
- [E1-T2: Scaffold web and backend applications](tasks/E1-T2-scaffold-web-and-backend-applications.md) — promoted, `done`, P0/M, M1
- [E1-T4: Establish CI baseline](tasks/E1-T4-establish-ci-baseline.md) — promoted, `done`, P0/M, M1
- [E1-T3: Add local Docker Compose](tasks/E1-T3-add-local-docker-compose.md) — promoted, `done`, P0/M, M1
- [E1-T5: Configure protected-main governance](proposed-tasks/E1-T5-configure-protected-main-governance.md) — `cancelled`, P0/M, M1
- [E1-T6: Configure Dependabot update pull requests](tasks/E1-T6-configure-dependabot-update-pull-requests.md) — promoted, `done`, P0/M, M1
- [E1-T7: Implement scheduled Dependabot merge controller](proposed-tasks/E1-T7-implement-scheduled-dependabot-merge-controller.md) — `proposed`, P0/M, M1

## Cross-epic dependencies

- Incoming: E1-T2 depends on E0-T2.
- Outgoing: E0-T1 and E0-T2 depend on E1-T1.
- Outgoing: E2-T1 depends on E1-T2.
- Outgoing: E3-T1 depends on E1-T3.
- Outgoing: E5-T1 depends on E1-T2.
- Outgoing: E6-T4 depends on E1-T2.
- Outgoing: E7-T1 depends on E1-T3.
- Outgoing: E7-T3 depends on E1-T4.

The exact normalized dependency and traceability registry is maintained in the [epics index](../README.md). Promoted tasks are authoritative under `tasks/`; remaining candidates are authoritative only in their linked `proposed-tasks/` files.

## Lifecycle

Follow the [approval-gated workflow](../../workflow/README.md), [proposed-task schema](../../workflow/templates/PROPOSED_TASK.md), [implementation-plan schema](../../workflow/templates/IMPLEMENTATION_PLAN.md), and [definition of done](../../workflow/DEFINITION_OF_DONE.md). Priority, roadmap order, or epic selection never bypasses owner approvals, promotion, completed dependencies, or one-branch-per-task gates.
