---
schema: ai-workflow/epic@1
id: E7
title: "Docker/GitHub production delivery"
status: draft
milestones: [M3]
owner: owner
spike: SPIKE.md
implementation_plan: IMPLEMENTATION_PLAN.md
---

# E7: Docker/GitHub production delivery

## Outcome

every merge to `main` can produce a verified, rollback-capable release on the supplied server.

## Approval state

- Epic workspace status: `draft`.
- [Spike](SPIKE.md): `draft`, revision 1, owner approval pending, research only, no code.
- [Implementation plan](IMPLEMENTATION_PLAN.md): `draft`, revision 1, blocked with no approved spike revision and no executable task sequence.
- Every file in `proposed-tasks/` is non-actionable. No implementation, scaffold, migration, infrastructure change, generated executable artifact, or proof code is approved.
- No `tasks/` directory exists; it may be created only when an approved candidate is promoted after spike approval.

## Milestones

[M3](../../milestones/M3-public-dockerized-mvp.md)

## Governing domain documents

- [Operations](../../operations/README.md)
- [Governance](../../governance/README.md)
- [Security](../../security/README.md)
- [Data](../../data/README.md)
- [Decisions](../../decisions/README.md)

## Governing decisions and deferred gates

- [ADR-005](../../decisions/adr/ADR-005-postgresql-postgis.md)
- [ADR-006](../../decisions/adr/ADR-006-shared-ingestion-core.md)
- [ADR-007](../../decisions/adr/ADR-007-mounted-media-storage-interface.md)
- [ADR-008](../../decisions/adr/ADR-008-single-server-immutable-deployments.md)
- [ADR-009](../../decisions/adr/ADR-009-feature-branch-development.md)
- [ADR-010](../../decisions/adr/ADR-010-isolate-wef-shared-nuc.md)
- [ADR-011](../../decisions/adr/ADR-011-accounts-gate-contact-reveal.md)
- [ADR-013](../../decisions/adr/ADR-013-committed-openapi-offline-docs.md)
- [ADR-014](../../decisions/adr/ADR-014-actions-owned-deploy-configuration.md)
- [ADR-015](../../decisions/adr/ADR-015-defer-backups.md)
- [ADR-016](../../decisions/adr/ADR-016-pseudonymous-accounts-owner-console.md)
- [ADR-017](../../decisions/adr/ADR-017-no-enforced-branch-protection.md)
- [D-001](../../decisions/deferred/D-001-production-server-domain.md)
- [D-002](../../decisions/deferred/D-002-recurring-geocoding-provider.md)

## Proposed tasks

- [E7-T1: Build production Compose topology](proposed-tasks/E7-T1-build-production-compose-topology.md) — `proposed`, P1/L, M3
- [E7-T2: Provision and verify supplied server](proposed-tasks/E7-T2-provision-and-verify-supplied-server.md) — `proposed`, P1/M, M3
- [E7-T3: Implement GitHub image and deployment workflows](proposed-tasks/E7-T3-implement-github-image-and-deployment-workflows.md) — `proposed`, P1/L, M3
- [E7-T4: Implement health verification and rollback](proposed-tasks/E7-T4-implement-health-verification-and-rollback.md) — `proposed`, P1/M, M3
- [E7-T5: Future backup and restore capability](proposed-tasks/E7-T5-future-backup-and-restore-capability.md) — `deferred`, P2/L, M3
- [E7-T6: Transfer and import the historical dataset](proposed-tasks/E7-T6-transfer-and-import-the-historical-dataset.md) — `proposed`, P1/L, M3
- [E7-T7: Enable production registration and contact reveal](proposed-tasks/E7-T7-enable-production-registration-and-contact-reveal.md) — `proposed`, P1/M, M3

## Cross-epic dependencies

- Incoming: E7-T1 depends on E1-T3.
- Incoming: E7-T1 depends on E6-T2.
- Incoming: E7-T1 depends on E6-T3.
- Incoming: E7-T3 depends on E1-T4.
- Incoming: E7-T6 depends on E3-T5.
- Incoming: E7-T7 depends on E6-T4.
- Incoming: E7-T7 depends on E6-T5.
- Incoming: E7-T7 depends on E6-T6.
- Incoming: E7-T7 depends on E6-T7.

The exact normalized dependency and traceability registry is maintained in the [epics index](../README.md). Each workflow candidate is authoritative only in the single linked `proposed-tasks/` file above; its `legacy-roadmap:*` source value records non-path provenance.

## Lifecycle

Follow the [approval-gated workflow](../../workflow/README.md), [proposed-task schema](../../workflow/templates/PROPOSED_TASK.md), [implementation-plan schema](../../workflow/templates/IMPLEMENTATION_PLAN.md), and [definition of done](../../workflow/DEFINITION_OF_DONE.md). Priority, roadmap order, or epic selection never bypasses owner approvals, promotion, completed dependencies, or one-branch-per-task gates.
