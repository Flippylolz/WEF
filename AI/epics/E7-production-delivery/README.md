---
schema: ai-workflow/epic@1
id: E7
title: "Docker/GitHub production delivery"
status: ready
milestones: [M3]
owner: owner
spike: SPIKE.md
implementation_plan: IMPLEMENTATION_PLAN.md
---

# E7: Docker/GitHub production delivery

## Outcome

every merge to `main` can produce a verified, rollback-capable release on the supplied server.

## Approval state

- Epic workspace status: `ready`; the anonymous rehearsal remains complete while historical snapshot transfer is prioritized.
- [Spike](SPIKE.md): `approved`, revision 4, selecting selective E3-T5 snapshot transfer and non-public production candidate staging.
- [Implementation plan](IMPLEMENTATION_PLAN.md): revision 4 `approved` by Flippylolz on 2026-08-16; it sequences only E7-T6 revision 3.
- E7-T1 through E7-T4, E7-T6, and E7-T8 are `done`; E7-T8's 2026-08-15 invalidation was an accidental touch by another agent's E7-T6 priority work and was restored by the owner on 2026-08-16 (completion on PR #69). E7-T9 remains paused/invalidated. E7-T11 is proposed for the ADR-019-gated public activation, and E7-T10 remains proposed behind D-009. E7-T5 remains deferred and E7-T7 remains proposed.

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
- [ADR-018](../../decisions/adr/ADR-018-ordered-stacked-pull-requests.md)
- [ADR-019](../../decisions/adr/ADR-019-anonymous-http-production-rehearsal.md)
- [ADR-020](../../decisions/adr/ADR-020-use-nginx-shared-tls-ingress.md)
- [D-001](../../decisions/deferred/D-001-production-server-domain.md)
- [D-002](../../decisions/deferred/D-002-recurring-geocoding-provider.md)
- [D-009](../../decisions/deferred/D-009-shared-tls-hostnames-and-forwarding.md)

## Promoted tasks

- [E7-T1: Build production Compose topology](tasks/E7-T1-build-production-compose-topology.md) — `done`, P0/L, M3
- [E7-T2: Provision and verify supplied server](tasks/E7-T2-provision-and-verify-supplied-server.md) — `done`, P0/M, M3
- [E7-T3: Implement GitHub image and deployment workflows](tasks/E7-T3-implement-github-image-and-deployment-workflows.md) — `done`, P0/L, M3
- [E7-T4: Implement health verification and rollback](tasks/E7-T4-implement-health-verification-and-rollback.md) — `done`, P0/M, M3
- [E7-T8: Build isolated shared Nginx TLS topology](tasks/E7-T8-build-shared-nginx-tls-ingress.md) — `done` through PR #69 (gates restored by owner after an accidental invalidation), P1/M, M3
- [E7-T9: Implement reversible shared-edge cutover](tasks/E7-T9-implement-reversible-shared-edge-cutover.md) — `invalidated`/paused; dependency E7-T8 is now satisfied but its own gates await the owner's call, P1/L, M3
- [E7-T6: Transfer the verified historical snapshot into a non-public production candidate](tasks/E7-T6-transfer-and-import-the-historical-dataset.md) — `done` through PRs #88–#102, P1/L, M3

## Deferred/proposed tasks

- [E7-T5: Future backup and restore capability](proposed-tasks/E7-T5-future-backup-and-restore-capability.md) — `deferred`, P2/L, M3
- [E7-T7: Enable production registration and contact reveal](proposed-tasks/E7-T7-enable-production-registration-and-contact-reveal.md) — `proposed`, P1/M, M3
- [E7-T10: Roll out and verify shared TLS](proposed-tasks/E7-T10-roll-out-and-verify-shared-tls.md) — `proposed`, P1/M, M3
- [E7-T11: Activate the verified historical candidate publicly](proposed-tasks/E7-T11-activate-the-verified-historical-candidate.md) — `proposed` revision 1, P1/M, M3; ADR-019 activation boundary behind E7-T6, E7-T10, and E7-T7

## Cross-epic dependencies

- Incoming: E7-T1 depends on E1-T3 and the E5-T1 anonymous browser MVP.
- Incoming: E7-T3 depends on E1-T4.
- Incoming: E7-T6 depends on E3-T5.
- Incoming: E7-T7 depends on E6-T4.
- Incoming: E7-T7 depends on E6-T5.
- Incoming: E7-T7 depends on E6-T6.
- Incoming: E7-T7 depends on E6-T7.
- Incoming: E7-T7 depends on E7-T10.
- Incoming: E7-T11 depends on E7-T6, E7-T10, and E7-T7.
- E7-T8 depends on completed E7-T4.
- E7-T9 depends on E7-T8.
- E7-T10 depends on E7-T9 and D-009 hostname/router resolution.

The exact normalized dependency and traceability registry is maintained in the [epics index](../README.md). Each workflow candidate is authoritative only in the single linked `proposed-tasks/` file above; its `legacy-roadmap:*` source value records non-path provenance.

## Lifecycle

Follow the [approval-gated workflow](../../workflow/README.md), [proposed-task schema](../../workflow/templates/PROPOSED_TASK.md), [implementation-plan schema](../../workflow/templates/IMPLEMENTATION_PLAN.md), and [definition of done](../../workflow/DEFINITION_OF_DONE.md). Priority, roadmap order, or epic selection never bypasses owner approvals, promotion, completed dependencies, or one-branch-per-task gates.
