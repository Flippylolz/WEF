---
schema: ai-workflow/proposed-task@1
id: E4-T1
epic: E4
title: "Implement map query service and GeoJSON endpoint"
status: proposed
revision: 1
actionable: false
priority: P0
size: L
milestone: M1
dependencies: [E3-T1, E3-T3]
requirement_ids: [P-001, P-003]
decision_ids: [ADR-002, ADR-003, ADR-005, ADR-012, ADR-013]
deferred_decision_ids: []
source: "legacy-roadmap:E4-T1"
promotion:
  status: not_promoted
  target: null
  promoted_by: null
  promoted_at: null
---

# E4-T1: Implement map query service and GeoJSON endpoint

> This candidate is planning input only. It is not approved, scheduled, ready, or in progress.

## Outcome

Contribute the independently reviewable result described by **Implement map query service and GeoJSON endpoint** to the epic outcome: stable, efficient public endpoints that implement filter semantics once.

## Original roadmap definition

The following definition preserves the original E4-T1 roadmap entry:

- Priority/size: P0 / L
- Dependencies: E3-T1, E3-T3
- Work:
  - Validate bounding box and all filter groups.
  - Query grouped locations with matching/total counts and latest publication date.
  - Return compact GeoJSON plus request metadata/ETag.
- Acceptance:
  - Contract matches [HTTP API contract](../../../contracts/HTTP_API.md).
  - Range intersection, null behavior, AND/OR rules, in-scope visibility, and coordinate order have integration tests.
  - The M1 fixture returns grouped pins and dates.

## Scope and approval boundary

- Preserve the roadmap work and acceptance criteria above for refinement against the owner-approved spike.
- Do not treat this file, its priority, its branch note, or its roadmap ordering as permission to implement.
- Production code, scaffolds, migrations, infrastructure changes, and disposable proof code remain out of scope until promotion and current implementation-plan approval.

## Dependencies and traceability

- Task dependencies: [E3-T1](../../E3-database-geocoding-media/proposed-tasks/E3-T1-create-schema-and-migrations.md), [E3-T3](../../E3-database-geocoding-media/proposed-tasks/E3-T3-implement-geocoder-abstraction-and-cache.md)
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
