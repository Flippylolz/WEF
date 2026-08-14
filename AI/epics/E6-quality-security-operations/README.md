---
schema: ai-workflow/epic@1
id: E6
title: "Quality, security, and operations"
status: in_progress
milestones: [M3]
owner: owner
spike: SPIKE.md
implementation_plan: IMPLEMENTATION_PLAN.md
---

# E6: Quality, security, and operations

## Outcome

production behavior is tested, privacy-aware, observable, and recoverable.

## Approval state

- Epic workspace status: `in_progress`; E6-T4 is being implemented on its dedicated branch.
- [Spike](SPIKE.md): `approved`, revision 2 (PR #49, squash cd2ad36). It records the 2026-08-14 repository survey, the E6 dependency reality (only E6-T4 is actionable), and recommends the project-owned `pwdlib[argon2]` identity implementation for E6-T4.
- [Implementation plan](IMPLEMENTATION_PLAN.md): `approved`, revision 2 (`spike_revision: 2`, PR #50, squash bd4d34f), sequencing E6-T4 only.
- E6-T4 is `in_progress` on `feature/E6-T4-registration-sessions` with all gates satisfied.
- Every remaining file in `proposed-tasks/` is non-actionable. No implementation beyond the approved E6-T4 sequence is approved.

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

## Promoted tasks

- [E6-T4: Implement in-house registration and sessions](tasks/E6-T4-implement-in-house-registration-and-sessions.md) — `in_progress`, P1/L, M3; branch `feature/E6-T4-registration-sessions`

## Proposed tasks

- [E6-T1: Complete automated test pyramid](proposed-tasks/E6-T1-complete-automated-test-pyramid.md) — `proposed`, P1/L, M3; blocked on E4-T3/E5-T3
- [E6-T2: Perform privacy and security hardening](proposed-tasks/E6-T2-perform-privacy-and-security-hardening.md) — `proposed`, P1/M, M3; blocked on E3-T4/E4-T3/E5-T3
- [E6-T3: Add operational diagnostics](proposed-tasks/E6-T3-add-operational-diagnostics.md) — `proposed`, P1/M, M3; blocked on E3-T2/E4-T4
- [E6-T5: Implement contact masking, encryption, reveal, and audit](proposed-tasks/E6-T5-implement-contact-masking-encryption-reveal-and-audit.md) — `proposed`, P1/L, M3; blocked on E4-T3 and E6-T4
- [E6-T6: Implement English i18n and restricted-action UX](proposed-tasks/E6-T6-implement-english-i18n-and-restricted-action-ux.md) — `proposed`, P1/L, M3; blocked on E5-T3/E6-T4/E6-T5
- [E6-T7: Implement owner administration console](proposed-tasks/E6-T7-implement-owner-administration-console.md) — `proposed`, P1/L, M3; blocked on E6-T4/E6-T5

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
