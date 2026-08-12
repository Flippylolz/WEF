---
schema: ai-workflow/proposed-task@1
id: E6-T3
epic: E6
title: "Add operational diagnostics"
status: proposed
revision: 1
actionable: false
priority: P1
size: M
milestone: M3
dependencies: [E3-T2, E4-T4]
requirement_ids: [P-007]
decision_ids: [ADR-008, ADR-010, ADR-014, ADR-015]
deferred_decision_ids: []
source: "legacy-roadmap:E6-T3"
promotion:
  status: not_promoted
  target: null
  promoted_by: null
  promoted_at: null
---

# E6-T3: Add operational diagnostics

> This candidate is planning input only. It is not approved, scheduled, ready, or in progress.

## Outcome

Contribute the independently reviewable result described by **Add operational diagnostics** to the epic outcome: production behavior is tested, privacy-aware, observable, and recoverable.

## Original roadmap definition

The following definition preserves the original E6-T3 roadmap entry:

- Priority/size: P1 / M
- Dependencies: E3-T2, E4-T4
- Work:
  - Add structured logs, release/request/run IDs, liveness/readiness, import metrics, rotation, and non-sensitive diagnostics.
- Acceptance:
  - An operator can identify release, failed stage/reason, disk usage, and last successful import without reading source content.

## Scope and approval boundary

- Preserve the roadmap work and acceptance criteria above for refinement against the owner-approved spike.
- Do not treat this file, its priority, its branch note, or its roadmap ordering as permission to implement.
- Production code, scaffolds, migrations, infrastructure changes, and disposable proof code remain out of scope until promotion and current implementation-plan approval.

## Dependencies and traceability

- Task dependencies: [E3-T2](../../E3-database-geocoding-media/proposed-tasks/E3-T2-implement-idempotent-persistence-and-reprocessing.md), [E4-T4](../../E4-read-api-filter-contracts/proposed-tasks/E4-T4-harden-api-behavior-and-performance.md)
- Milestone: [M3](../../../milestones/M3-public-dockerized-mvp.md).
- Traceability: [Product requirements](../../../product/EXPERIENCE.md), [Decision registry](../../../decisions/README.md), [Product](../../../product/README.md), [Security](../../../security/README.md), [Operations](../../../operations/README.md), [Governance](../../../governance/README.md), [Contracts](../../../contracts/README.md).

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
