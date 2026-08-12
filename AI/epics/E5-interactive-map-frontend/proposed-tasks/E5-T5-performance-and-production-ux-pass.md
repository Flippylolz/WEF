---
schema: ai-workflow/proposed-task@1
id: E5-T5
epic: E5
title: "Performance and production UX pass"
status: proposed
revision: 1
actionable: false
priority: P1
size: M
milestone: M3
dependencies: [E5-T4, E4-T4]
requirement_ids: [P-001, P-004, P-005]
decision_ids: [ADR-004, ADR-007, ADR-012]
deferred_decision_ids: []
source: "legacy-roadmap:E5-T5"
promotion:
  status: not_promoted
  target: null
  promoted_by: null
  promoted_at: null
---

# E5-T5: Performance and production UX pass

> This candidate is planning input only. It is not approved, scheduled, ready, or in progress.

## Outcome

Contribute the independently reviewable result described by **Performance and production UX pass** to the epic outcome: a responsive, accessible map/list/detail experience over dated offers.

## Original roadmap definition

The following definition preserves the original E5-T5 roadmap entry:

- Priority/size: P1 / M
- Dependencies: E5-T4, E4-T4
- Work:
  - Optimize bundles/images, prevent map reinitialization, add metadata/error boundaries, and measure web vitals.
- Acceptance:
  - First useful map/controls meet the target on the agreed test profile.
  - Full detail/media is absent from initial map payload.
  - Tile/API outages preserve filters and provide useful recovery actions.

## Scope and approval boundary

- Preserve the roadmap work and acceptance criteria above for refinement against the owner-approved spike.
- Do not treat this file, its priority, its branch note, or its roadmap ordering as permission to implement.
- Production code, scaffolds, migrations, infrastructure changes, and disposable proof code remain out of scope until promotion and current implementation-plan approval.

## Dependencies and traceability

- Task dependencies: [E5-T4](E5-T4-complete-responsive-list-map-accessibility.md), [E4-T4](../../E4-read-api-filter-contracts/proposed-tasks/E4-T4-harden-api-behavior-and-performance.md)
- Milestone: [M3](../../../milestones/M3-public-dockerized-mvp.md).
- Traceability: [Product requirements](../../../product/EXPERIENCE.md), [Decision registry](../../../decisions/README.md), [Product](../../../product/README.md), [Contracts](../../../contracts/README.md), [Architecture](../../../architecture/README.md), [Security](../../../security/README.md).

## Risks and notes

- Material changes to scope, dependencies, acceptance, contracts, security, ingestion, deployment, or rollback require workflow revalidation and approval.
- The exact roadmap priority/size is `P1 / M`.
- This task definition is authoritative only in this `proposed-tasks/` location until a valid promotion moves it to `tasks/`.

## Promotion checklist

- [ ] The epic spike is explicitly owner-approved for its current revision.
- [ ] Scope, acceptance criteria, dependencies, priority, size, and traceability have been reviewed against that spike.
- [ ] Required deferred decisions and milestone prerequisites are resolved.
- [ ] The file will be moved—not copied—to `tasks/` and converted to `ai-workflow/task@1`.
- [ ] Promotion metadata will identify the target, promoter, and timestamp.
