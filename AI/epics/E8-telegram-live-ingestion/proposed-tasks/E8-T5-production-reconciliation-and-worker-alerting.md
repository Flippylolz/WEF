---
schema: ai-workflow/proposed-task@1
id: E8-T5
epic: E8
title: "Production reconciliation and worker alerting"
status: proposed
revision: 1
actionable: false
priority: P2
size: L
milestone: M4
dependencies: [E8-T3, E8-T4]
requirement_ids: [P-006, P-007]
decision_ids: [ADR-006, ADR-010, ADR-015]
deferred_decision_ids: []
source: "legacy-roadmap:E8-T5"
promotion:
  status: not_promoted
  target: null
  promoted_by: null
  promoted_at: null
---

# E8-T5: Production reconciliation and worker alerting

> This candidate is planning input only. It is not approved, scheduled, ready, or in progress.

## Outcome

Contribute the independently reviewable result described by **Production reconciliation and worker alerting** to the epic outcome: new, edited, and deleted channel posts are processed safely without changing public contracts.

## Original roadmap definition

The following definition preserves the original E8-T5 roadmap entry:

- Priority/size: P2 / L
- Dependencies: E8-T3, E8-T4
- Work:
  - Reconcile overlap from the export checkpoint, deploy one worker, add stale-event/connectivity alerts, and rehearse session rotation.
- Acceptance:
  - No source-message gaps or duplicate canonical offers are unexplained.
  - Last received/committed timestamps are observable.
  - Rotation and outage recovery complete without full re-import.

## Scope and approval boundary

- Preserve the roadmap work and acceptance criteria above for refinement against the owner-approved spike.
- Do not treat this file, its priority, its branch note, or its roadmap ordering as permission to implement.
- Production code, scaffolds, migrations, infrastructure changes, and disposable proof code remain out of scope until promotion and current implementation-plan approval.

## Dependencies and traceability

- Task dependencies: [E8-T3](E8-T3-implement-live-new-edit-delete-processing.md), [E8-T4](../tasks/E8-T4-revalidate-geocoder-for-recurring-ingestion.md)
- Milestone: [M4](../../../milestones/M4-live-telegram-updates.md).
- Traceability: [Product requirements](../../../product/EXPERIENCE.md), [Decision registry](../../../decisions/README.md), [Ingestion](../../../ingestion/README.md), [Data](../../../data/README.md), [Operations](../../../operations/README.md), [Security](../../../security/README.md).

## Risks and notes

- Material changes to scope, dependencies, acceptance, contracts, security, ingestion, deployment, or rollback require workflow revalidation and approval.
- The exact roadmap priority/size is `P2 / L`.
- This task definition is authoritative only in this `proposed-tasks/` location until a valid promotion moves it to `tasks/`.

## Promotion checklist

- [ ] The epic spike is explicitly owner-approved for its current revision.
- [ ] Scope, acceptance criteria, dependencies, priority, size, and traceability have been reviewed against that spike.
- [ ] Required deferred decisions and milestone prerequisites are resolved.
- [ ] The file will be moved—not copied—to `tasks/` and converted to `ai-workflow/task@1`.
- [ ] Promotion metadata will identify the target, promoter, and timestamp.
