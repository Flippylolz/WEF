---
schema: ai-workflow/proposed-task@1
id: E3-T1
epic: E3
title: "Create schema and migrations"
status: proposed
revision: 1
actionable: false
priority: P0
size: L
milestone: M1
dependencies: [E1-T3]
requirement_ids: [P-001, P-002, P-006, P-007, P-008]
decision_ids: [ADR-003, ADR-005, ADR-006, ADR-007, ADR-011, ADR-016]
deferred_decision_ids: []
source: "legacy-roadmap:E3-T1"
promotion:
  status: not_promoted
  target: null
  promoted_by: null
  promoted_at: null
---

# E3-T1: Create schema and migrations

> This candidate is planning input only. It is not approved, scheduled, ready, or in progress.

## Outcome

Contribute the independently reviewable result described by **Create schema and migrations** to the epic outcome: idempotent canonical data and web-safe media with reviewed map coordinates.

## Original roadmap definition

The following definition preserves the original E3-T1 roadmap entry:

- Priority/size: P0 / L
- Dependencies: E1-T3
- Work:
  - Implement entities, constraints, enums, and baseline indexes from [data model](../../../contracts/DATA_MODEL.md).
  - Add clean-install and previous-revision migration tests.
- Acceptance:
  - Schema upgrades an empty PostGIS database.
  - Source uniqueness and spatial indexes are verified.
  - No real-world availability boolean exists.

## Scope and approval boundary

- Preserve the roadmap work and acceptance criteria above for refinement against the owner-approved spike.
- Do not treat this file, its priority, its branch note, or its roadmap ordering as permission to implement.
- Production code, scaffolds, migrations, infrastructure changes, and disposable proof code remain out of scope until promotion and current implementation-plan approval.

## Dependencies and traceability

- Task dependencies: [E1-T3](../../E1-repository-developer-foundation/tasks/E1-T3-add-local-docker-compose.md)
- Milestone: [M1](../../../milestones/M1-vertical-proof.md).
- Traceability: [Product requirements](../../../product/EXPERIENCE.md), [Decision registry](../../../decisions/README.md), [Data](../../../data/README.md), [Contracts](../../../contracts/README.md), [Ingestion](../../../ingestion/README.md), [Security](../../../security/README.md).

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
