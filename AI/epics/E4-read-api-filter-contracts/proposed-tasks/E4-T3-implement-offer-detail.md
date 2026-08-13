---
schema: ai-workflow/proposed-task@1
id: E4-T3
epic: E4
title: "Implement offer detail"
status: proposed
revision: 1
actionable: false
priority: P0
size: M
milestone: M2
dependencies: [E3-T4, E4-T2]
requirement_ids: [P-002, P-005, P-006, P-007, P-008]
decision_ids: [ADR-003, ADR-007, ADR-011, ADR-012, ADR-013, ADR-016]
deferred_decision_ids: []
source: "legacy-roadmap:E4-T3"
promotion:
  status: not_promoted
  target: null
  promoted_by: null
  promoted_at: null
---

# E4-T3: Implement offer detail

> This candidate is planning input only. It is not approved, scheduled, ready, or in progress.

## Outcome

Contribute the independently reviewable result described by **Implement offer detail** to the epic outcome: stable, efficient public endpoints that implement filter semantics once.

## Original roadmap definition

The following definition preserves the original E4-T3 roadmap entry:

- Priority/size: P0 / M
- Dependencies: E3-T4, E4-T2
- Work:
  - Return dated typed fields, safe source text, media, confidence, source history, and verified Telegram link.
- Acceptance:
  - No raw payload, local path, dedicated contact field, or unverified link is exposed.
  - Missing media/link cases remain valid responses.
  - Public schema is represented in OpenAPI/frontend types.

## Scope and approval boundary

- Preserve the roadmap work and acceptance criteria above for refinement against the owner-approved spike.
- Do not treat this file, its priority, its branch note, or its roadmap ordering as permission to implement.
- Production code, scaffolds, migrations, infrastructure changes, and disposable proof code remain out of scope until promotion and current implementation-plan approval.

## Dependencies and traceability

- Task dependencies: [E3-T4](../../E3-database-geocoding-media/proposed-tasks/E3-T4-implement-media-storage-and-derivatives.md), [E4-T2](../tasks/E4-T2-implement-facets-and-location-offer-collection.md)
- Milestone: [M2](../../../milestones/M2-historical-dataset-ready.md).
- Traceability: [Product requirements](../../../product/EXPERIENCE.md), [Decision registry](../../../decisions/README.md), [Product](../../../product/README.md), [Contracts](../../../contracts/README.md), [Architecture](../../../architecture/README.md), [Security](../../../security/README.md).

## Risks and notes

- Material changes to scope, dependencies, acceptance, contracts, security, ingestion, deployment, or rollback require workflow revalidation and approval.
- The exact roadmap priority/size is `P0 / M`.
- This task definition is authoritative only in this `proposed-tasks/` location until a valid promotion moves it to `tasks/`.

## Promotion checklist

- [ ] The epic spike is explicitly owner-approved for its current revision.
- [ ] Scope, acceptance criteria, dependencies, priority, size, and traceability have been reviewed against that spike.
- [ ] Required deferred decisions and milestone prerequisites are resolved.
- [ ] The file will be moved—not copied—to `tasks/` and converted to `ai-workflow/task@1`.
- [ ] Promotion metadata will identify the target, promoter, and timestamp.
