---
schema: ai-workflow/epic@1
id: E6
title: "Quality, security, and operations"
status: draft
milestones: [M3]
owner: owner
spike: SPIKE.md
implementation_plan: IMPLEMENTATION_PLAN.md
---

# E6: Quality, security, and operations

## Outcome

production behavior is tested, privacy-aware, observable, and recoverable.

## Approval state

- Epic workspace status: `draft`.
- [Spike](SPIKE.md): `draft`, revision 1, owner approval pending, research only, no code.
- [Implementation plan](IMPLEMENTATION_PLAN.md): `draft`, revision 1, blocked with no approved spike revision and no executable task sequence.
- Every file in `proposed-tasks/` is non-actionable. No implementation, scaffold, migration, infrastructure change, generated executable artifact, or proof code is approved.
- No `tasks/` directory exists; it may be created only when an approved candidate is promoted after spike approval.

## Milestones

[M3](../../milestones/M3-public-dockerized-mvp.md)

## Governing domain documents

- [Product](../../product/README.md)
- [Security](../../security/README.md)
- [Operations](../../operations/README.md)
- [Governance](../../governance/README.md)
- [Contracts](../../contracts/README.md)
- [Decisions](../../decisions/README.md)

## Governing decisions and deferred gates

- [ADR-007](../../decisions/adr/ADR-007-mounted-media-storage-interface.md)
- [ADR-008](../../decisions/adr/ADR-008-single-server-immutable-deployments.md)
- [ADR-010](../../decisions/adr/ADR-010-isolate-wef-shared-nuc.md)
- [ADR-011](../../decisions/adr/ADR-011-accounts-gate-contact-reveal.md)
- [ADR-012](../../decisions/adr/ADR-012-backend-centric-modular-monolith.md)
- [ADR-013](../../decisions/adr/ADR-013-committed-openapi-offline-docs.md)
- [ADR-014](../../decisions/adr/ADR-014-actions-owned-deploy-configuration.md)
- [ADR-015](../../decisions/adr/ADR-015-defer-backups.md)
- [ADR-016](../../decisions/adr/ADR-016-pseudonymous-accounts-owner-console.md)

## Proposed tasks

- [E6-T1: Complete automated test pyramid](proposed-tasks/E6-T1-complete-automated-test-pyramid.md) — `proposed`, P1/L, M3
- [E6-T2: Perform privacy and security hardening](proposed-tasks/E6-T2-perform-privacy-and-security-hardening.md) — `proposed`, P1/M, M3
- [E6-T3: Add operational diagnostics](proposed-tasks/E6-T3-add-operational-diagnostics.md) — `proposed`, P1/M, M3
- [E6-T4: Implement in-house registration and sessions](proposed-tasks/E6-T4-implement-in-house-registration-and-sessions.md) — `proposed`, P1/L, M3
- [E6-T5: Implement contact masking, encryption, reveal, and audit](proposed-tasks/E6-T5-implement-contact-masking-encryption-reveal-and-audit.md) — `proposed`, P1/L, M3
- [E6-T6: Implement English i18n and restricted-action UX](proposed-tasks/E6-T6-implement-english-i18n-and-restricted-action-ux.md) — `proposed`, P1/L, M3
- [E6-T7: Implement owner administration console](proposed-tasks/E6-T7-implement-owner-administration-console.md) — `proposed`, P1/L, M3

## Cross-epic dependencies

- Incoming: E6-T1 depends on E4-T3.
- Incoming: E6-T1 depends on E5-T3.
- Incoming: E6-T2 depends on E3-T4.
- Incoming: E6-T2 depends on E4-T3.
- Incoming: E6-T2 depends on E5-T3.
- Incoming: E6-T3 depends on E3-T2.
- Incoming: E6-T3 depends on E4-T4.
- Incoming: E6-T4 depends on E1-T2.
- Incoming: E6-T4 depends on E3-T1.
- Incoming: E6-T5 depends on E2-T2.
- Incoming: E6-T5 depends on E3-T1.
- Incoming: E6-T5 depends on E4-T3.
- Incoming: E6-T6 depends on E5-T3.
- Outgoing: E7-T1 depends on E6-T2.
- Outgoing: E7-T1 depends on E6-T3.
- Outgoing: E7-T7 depends on E6-T4.
- Outgoing: E7-T7 depends on E6-T5.
- Outgoing: E7-T7 depends on E6-T6.
- Outgoing: E7-T7 depends on E6-T7.

The exact normalized dependency and traceability registry is maintained in the [epics index](../README.md). Each workflow candidate is authoritative only in the single linked `proposed-tasks/` file above; its `legacy-roadmap:*` source value records non-path provenance.

## Lifecycle

Follow the [approval-gated workflow](../../workflow/README.md), [proposed-task schema](../../workflow/templates/PROPOSED_TASK.md), [implementation-plan schema](../../workflow/templates/IMPLEMENTATION_PLAN.md), and [definition of done](../../workflow/DEFINITION_OF_DONE.md). Priority, roadmap order, or epic selection never bypasses owner approvals, promotion, completed dependencies, or one-branch-per-task gates.
