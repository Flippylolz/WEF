---
schema: ai-workflow/proposed-task@1
id: E5-T1
epic: E5
title: "Build map shell and grouped pin interaction"
status: proposed
revision: 1
actionable: false
priority: P0
size: L
milestone: M1
dependencies: [E1-T2, E4-T1]
requirement_ids: [P-001, P-004, P-007]
decision_ids: [ADR-002, ADR-004, ADR-012]
deferred_decision_ids: []
source: "legacy-roadmap:E5-T1"
promotion:
  status: not_promoted
  target: null
  promoted_by: null
  promoted_at: null
---

# E5-T1: Build map shell and grouped pin interaction

> This candidate is planning input only. It is not approved, scheduled, ready, or in progress.

## Outcome

Contribute the independently reviewable result described by **Build map shell and grouped pin interaction** to the epic outcome: a responsive, accessible map/list/detail experience over dated offers.

## Original roadmap definition

The following definition preserves the original E5-T1 roadmap entry:

- Priority/size: P0 / L
- Dependencies: E1-T2, E4-T1
- Work:
  - Add client-only MapLibre map with configurable OpenFreeMap style.
  - Render clustered GeoJSON, cluster expansion, selected pin, and result panel.
  - Add attribution and degraded WebGL/tile states.
- Acceptance:
  - M1 fixture renders a grouped pin and opens a dated location panel.
  - Cluster and pin interactions are keyboard/pointer testable where supported.
  - OpenStreetMap/OpenFreeMap attribution is visible.
  - Inferred/low-confidence location data is identified without relying on color alone.

## Scope and approval boundary

- Preserve the roadmap work and acceptance criteria above for refinement against the owner-approved spike.
- Do not treat this file, its priority, its branch note, or its roadmap ordering as permission to implement.
- Production code, scaffolds, migrations, infrastructure changes, and disposable proof code remain out of scope until promotion and current implementation-plan approval.

## Dependencies and traceability

- Task dependencies: [E1-T2](../../E1-repository-developer-foundation/proposed-tasks/E1-T2-scaffold-web-and-backend-applications.md), [E4-T1](../../E4-read-api-filter-contracts/proposed-tasks/E4-T1-implement-map-query-service-and-geojson-endpoint.md)
- Milestone: [M1](../../../milestones/M1-vertical-proof.md).
- Traceability: [Product requirements](../../../product/EXPERIENCE.md), [Decision registry](../../../decisions/README.md), [Product](../../../product/README.md), [Contracts](../../../contracts/README.md), [Architecture](../../../architecture/README.md), [Security](../../../security/README.md).

## Risks and notes

- Material changes to scope, dependencies, acceptance, contracts, security, ingestion, deployment, or rollback require workflow revalidation and approval.
- The exact roadmap priority/size is `P0 / L`.
- This task definition is authoritative only in this `proposed-tasks/` location until a valid promotion moves it to `tasks/`.

## Promotion checklist

- [ ] The epic spike is explicitly owner-approved for its current revision.
- [ ] Scope, acceptance criteria, dependencies, priority, size, and traceability have been reviewed against that spike.
- [ ] Required deferred decisions and milestone prerequisites are resolved.
- [ ] The file will be moved—not copied—to `tasks/` and converted to `ai-workflow/task@1`.
- [ ] Promotion metadata will identify the target, promoter, and timestamp.
