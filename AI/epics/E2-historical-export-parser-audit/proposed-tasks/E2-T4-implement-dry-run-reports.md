---
schema: ai-workflow/proposed-task@1
id: E2-T4
epic: E2
title: "Implement dry-run reports"
status: proposed
revision: 1
actionable: false
priority: P0
size: M
milestone: M2
dependencies: [E2-T2, E2-T3]
requirement_ids: [P-007]
decision_ids: [ADR-006]
deferred_decision_ids: []
source: "legacy-roadmap:E2-T4"
promotion:
  status: not_promoted
  target: null
  promoted_by: null
  promoted_at: null
---

# E2-T4: Implement dry-run reports

> This candidate is planning input only. It is not approved, scheduled, ready, or in progress.

## Outcome

Contribute the independently reviewable result described by **Implement dry-run reports** to the epic outcome: deterministic extraction from the raw Telegram export with reconciled dry-run reporting.

## Original roadmap definition

The following definition preserves the original E2-T4 roadmap entry:

- Priority/size: P0 / M
- Dependencies: E2-T2, E2-T3
- Work:
  - Produce machine-readable and human-readable reports defined in [data quality and readiness](../../../data/QUALITY_AND_READINESS.md).
  - Redact phone numbers, mentions, and source payloads from routine logs/samples.
- Acceptance:
  - Stage counts reconcile to input.
  - Failures have stable reason codes and redacted representative samples.
  - Dry run performs no source/location/offer/geocode/media writes and no media copies; it may persist only its isolated ingest-run metadata and report artifact.

## Scope and approval boundary

- Preserve the roadmap work and acceptance criteria above for refinement against the owner-approved spike.
- Do not treat this file, its priority, its branch note, or its roadmap ordering as permission to implement.
- Production code, scaffolds, migrations, infrastructure changes, and disposable proof code remain out of scope until promotion and current implementation-plan approval.

## Dependencies and traceability

- Task dependencies: [E2-T2](E2-T2-implement-candidate-detection-and-typed-extractors.md), [E2-T3](E2-T3-implement-media-grouping.md)
- Milestone: [M2](../../../milestones/M2-historical-dataset-ready.md).
- Traceability: [Product requirements](../../../product/EXPERIENCE.md), [Decision registry](../../../decisions/README.md), [Data](../../../data/README.md), [Ingestion](../../../ingestion/README.md), [Contracts](../../../contracts/README.md), [Security](../../../security/README.md).

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
