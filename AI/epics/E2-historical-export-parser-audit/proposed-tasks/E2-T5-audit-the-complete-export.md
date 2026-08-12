---
schema: ai-workflow/proposed-task@1
id: E2-T5
epic: E2
title: "Audit the complete export"
status: proposed
revision: 1
actionable: false
priority: P0
size: L
milestone: M2
dependencies: [E2-T4]
requirement_ids: [P-007]
decision_ids: [ADR-006]
deferred_decision_ids: []
source: "legacy-roadmap:E2-T5"
promotion:
  status: not_promoted
  target: null
  promoted_by: null
  promoted_at: null
---

# E2-T5: Audit the complete export

> This candidate is planning input only. It is not approved, scheduled, ready, or in progress.

## Outcome

Contribute the independently reviewable result described by **Audit the complete export** to the epic outcome: deterministic extraction from the raw Telegram export with reconciled dry-run reporting.

## Original roadmap definition

The following definition preserves the original E2-T5 roadmap entry:

- Priority/size: P0 / L
- Dependencies: E2-T4
- Work:
  - Run the parser over the complete source.
  - Review unknown templates, boundary cases, and candidate counts.
  - Add fixtures/rules for material gaps without overfitting.
- Acceptance:
  - The final report explains differences from the exploratory on-the-order-of-3,000 planning estimate and the reproducible token counters in [data source baseline](../../../data/SOURCE_BASELINE.md).
  - No unexplained record-count gap remains.
  - Parser version and source checksum make the audit reproducible.

## Scope and approval boundary

- Preserve the roadmap work and acceptance criteria above for refinement against the owner-approved spike.
- Do not treat this file, its priority, its branch note, or its roadmap ordering as permission to implement.
- Production code, scaffolds, migrations, infrastructure changes, and disposable proof code remain out of scope until promotion and current implementation-plan approval.

## Dependencies and traceability

- Task dependencies: [E2-T4](E2-T4-implement-dry-run-reports.md)
- Milestone: [M2](../../../milestones/M2-historical-dataset-ready.md).
- Traceability: [Product requirements](../../../product/EXPERIENCE.md), [Decision registry](../../../decisions/README.md), [Data](../../../data/README.md), [Ingestion](../../../ingestion/README.md), [Contracts](../../../contracts/README.md), [Security](../../../security/README.md).

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
