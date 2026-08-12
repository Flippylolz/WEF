---
schema: ai-workflow/proposed-task@1
id: E5-T4
epic: E5
title: "Complete responsive list/map accessibility"
status: proposed
revision: 1
actionable: false
priority: P1
size: L
milestone: M3
dependencies: [E5-T2, E5-T3]
requirement_ids: [P-001, P-002, P-003, P-004, P-005]
decision_ids: [ADR-002, ADR-004, ADR-012]
deferred_decision_ids: []
source: "legacy-roadmap:E5-T4"
promotion:
  status: not_promoted
  target: null
  promoted_by: null
  promoted_at: null
---

# E5-T4: Complete responsive list/map accessibility

> This candidate is planning input only. It is not approved, scheduled, ready, or in progress.

## Outcome

Contribute the independently reviewable result described by **Complete responsive list/map accessibility** to the epic outcome: a responsive, accessible map/list/detail experience over dated offers.

## Original roadmap definition

The following definition preserves the original E5-T4 roadmap entry:

- Priority/size: P1 / L
- Dependencies: E5-T2, E5-T3
- Work:
  - Add desktop split view, mobile bottom sheet/list mode, focus management, highlight coordination, empty/error/loading states, and WebGL fallback list.
- Acceptance:
  - Core flow works at 360 px and current desktop widths.
  - Hover/focus result-to-pin coordination and empty/loading/error/WebGL-fallback list states match P-004.
  - Keyboard-only flow can filter, select, inspect, close, and open a source link.
  - Automated accessibility checks pass, a manual screen-reader/focus review is recorded, and public flows meet the agreed WCAG 2.2 AA target.

## Scope and approval boundary

- Preserve the roadmap work and acceptance criteria above for refinement against the owner-approved spike.
- Do not treat this file, its priority, its branch note, or its roadmap ordering as permission to implement.
- Production code, scaffolds, migrations, infrastructure changes, and disposable proof code remain out of scope until promotion and current implementation-plan approval.

## Dependencies and traceability

- Task dependencies: [E5-T2](E5-T2-add-url-backed-filters-and-viewport-querying.md), [E5-T3](E5-T3-build-offer-detail-and-media-gallery.md)
- Milestone: [M3](../../../milestones/M3-public-dockerized-mvp.md).
- Traceability: [Product requirements](../../../product/EXPERIENCE.md), [Decision registry](../../../decisions/README.md), [Product](../../../product/README.md), [Contracts](../../../contracts/README.md), [Architecture](../../../architecture/README.md), [Security](../../../security/README.md).

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
