---
schema: ai-workflow/proposed-task@1
id: E6-T6
epic: E6
title: "Implement English i18n and restricted-action UX"
status: proposed
revision: 1
actionable: false
priority: P1
size: L
milestone: M3
dependencies: [E5-T3, E6-T4, E6-T5]
requirement_ids: [P-002, P-008]
decision_ids: [ADR-011, ADR-012, ADR-016]
deferred_decision_ids: []
source: "legacy-roadmap:E6-T6"
promotion:
  status: not_promoted
  target: null
  promoted_by: null
  promoted_at: null
---

# E6-T6: Implement English i18n and restricted-action UX

> This candidate is planning input only. It is not approved, scheduled, ready, or in progress.

## Outcome

Contribute the independently reviewable result described by **Implement English i18n and restricted-action UX** to the epic outcome: production behavior is tested, privacy-aware, observable, and recoverable.

## Original roadmap definition

The following definition preserves the original E6-T6 roadmap entry:

- Priority/size: P1 / L
- Dependencies: E5-T3, E6-T4, E6-T5
- Work:
  - Move all user-facing web/auth/error strings to English i18n keys.
  - Add register/login/password-change/session UI and masked-contact reveal flow with return-to-offer behavior.
- Acceptance:
  - Components contain no hardcoded user-facing copy outside reviewed catalogs.
  - Anonymous users can browse everything except restricted actions.
  - Reveal requires explicit click; successful values are not prefetched, persisted, or cached.
  - Keyboard/accessibility/error/rate-limit flows pass tests.

## Scope and approval boundary

- Preserve the roadmap work and acceptance criteria above for refinement against the owner-approved spike.
- Do not treat this file, its priority, its branch note, or its roadmap ordering as permission to implement.
- Production code, scaffolds, migrations, infrastructure changes, and disposable proof code remain out of scope until promotion and current implementation-plan approval.

## Dependencies and traceability

- Task dependencies: [E5-T3](../../E5-interactive-map-frontend/proposed-tasks/E5-T3-build-offer-detail-and-media-gallery.md), [E6-T4](E6-T4-implement-in-house-registration-and-sessions.md), [E6-T5](E6-T5-implement-contact-masking-encryption-reveal-and-audit.md)
- Milestone: [M3](../../../milestones/M3-public-dockerized-mvp.md).
- Traceability: [Product requirements](../../../product/EXPERIENCE.md), [Decision registry](../../../decisions/README.md), [Product](../../../product/README.md), [Security](../../../security/README.md), [Operations](../../../operations/README.md), [Governance](../../../governance/README.md), [Contracts](../../../contracts/README.md).

## Risks and notes

- Material changes to scope, dependencies, acceptance, contracts, security, ingestion, deployment, or rollback require workflow revalidation and approval.
- The exact roadmap priority/size is `P1 / L`.
- This task definition is authoritative only in this `proposed-tasks/` location until a valid promotion moves it to `tasks/`.

## Promotion checklist

- [ ] The epic spike is explicitly owner-approved for its current revision.
- [ ] Scope, acceptance criteria, dependencies, priority, size, and traceability have been reviewed against that spike.
- [ ] Required deferred decisions and milestone prerequisites are resolved.
- [ ] The file will be moved—not copied—to `tasks/` and converted to `ai-workflow/task@1`.
- [ ] Promotion metadata will identify the target, promoter, and timestamp.
