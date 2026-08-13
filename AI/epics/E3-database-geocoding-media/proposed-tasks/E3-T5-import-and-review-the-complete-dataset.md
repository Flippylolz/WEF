---
schema: ai-workflow/proposed-task@1
id: E3-T5
epic: E3
title: "Import and review the complete dataset"
status: proposed
revision: 1
actionable: false
priority: P0
size: L
milestone: M2
dependencies: [E2-T5, E3-T2, E3-T3, E3-T4]
requirement_ids: [P-001, P-002, P-005, P-007]
decision_ids: [ADR-003, ADR-005, ADR-006, ADR-007]
deferred_decision_ids: []
source: "legacy-roadmap:E3-T5"
promotion:
  status: not_promoted
  target: null
  promoted_by: null
  promoted_at: null
---

# E3-T5: Import and review the complete dataset

> This candidate is planning input only. It is not approved, scheduled, ready, or in progress.

## Outcome

Contribute the independently reviewable result described by **Import and review the complete dataset** to the epic outcome: idempotent canonical data and web-safe media with reviewed map coordinates.

## Original roadmap definition

The following definition preserves the original E3-T5 roadmap entry:

- Priority/size: P0 / L
- Dependencies: E2-T5, E3-T2, E3-T3, E3-T4
- Work:
  - Import raw/canonical records, geocode misses under policy, review ambiguous/out-of-area locations, and copy verified media.
  - Run integrity and storage checks.
- Acceptance:
  - Final import counts reconcile to the audited source.
  - Every visible pin has accepted coordinates and at least one dated offer.
  - Unparsed, ungeocoded, duplicate-suspect, out-of-area, and missing-media items remain reportable.

## Scope and approval boundary

- Preserve the roadmap work and acceptance criteria above for refinement against the owner-approved spike.
- Do not treat this file, its priority, its branch note, or its roadmap ordering as permission to implement.
- Production code, scaffolds, migrations, infrastructure changes, and disposable proof code remain out of scope until promotion and current implementation-plan approval.

## Dependencies and traceability

- Task dependencies: [E2-T5](../../E2-historical-export-parser-audit/tasks/E2-T5-audit-the-complete-export.md), [E3-T2](E3-T2-implement-idempotent-persistence-and-reprocessing.md), [E3-T3](E3-T3-implement-geocoder-abstraction-and-cache.md), [E3-T4](E3-T4-implement-media-storage-and-derivatives.md)
- Milestone: [M2](../../../milestones/M2-historical-dataset-ready.md).
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
