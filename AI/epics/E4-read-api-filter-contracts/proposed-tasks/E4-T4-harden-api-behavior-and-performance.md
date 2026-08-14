---
schema: ai-workflow/proposed-task@1
id: E4-T4
epic: E4
title: "Harden API behavior and performance"
status: proposed
revision: 1
actionable: false
priority: P1
size: M
milestone: M2
dependencies: [E4-T1, E4-T2, E4-T3, E3-T5]
requirement_ids: [P-001, P-002, P-003]
decision_ids: [ADR-012, ADR-013]
deferred_decision_ids: []
source: "legacy-roadmap:E4-T4"
promotion:
  status: not_promoted
  target: null
  promoted_by: null
  promoted_at: null
---

# E4-T4: Harden API behavior and performance

> This candidate is planning input only. It is not approved, scheduled, ready, or in progress.

## Outcome

Contribute the independently reviewable result described by **Harden API behavior and performance** to the epic outcome: stable, efficient public endpoints that implement filter semantics once.

## Original roadmap definition

The following definition preserves the original E4-T4 roadmap entry:

- Priority/size: P1 / M
- Dependencies: E4-T1, E4-T2, E4-T3, E3-T5
- Work:
  - Add problem responses, request IDs, caching/revalidation, query-plan tests, and abuse bounds.
- Acceptance:
  - Warsaw map query meets the 500 ms p95 target in a documented representative test.
  - Invalid/oversized requests fail predictably.
  - Logs contain no full source/contact data.

## Scope and approval boundary

- Preserve the roadmap work and acceptance criteria above for refinement against the owner-approved spike.
- Do not treat this file, its priority, its branch note, or its roadmap ordering as permission to implement.
- Production code, scaffolds, migrations, infrastructure changes, and disposable proof code remain out of scope until promotion and current implementation-plan approval.

## Dependencies and traceability

- Task dependencies: [E4-T1](../tasks/E4-T1-implement-map-query-service-and-geojson-endpoint.md), [E4-T2](../tasks/E4-T2-implement-facets-and-location-offer-collection.md), [E4-T3](E4-T3-implement-offer-detail.md), [E3-T5](../../E3-database-geocoding-media/tasks/E3-T5-import-and-review-the-complete-dataset.md)
- Milestone: [M2](../../../milestones/M2-historical-dataset-ready.md).
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
