---
schema: ai-workflow/proposed-task@1
id: E2-T1
epic: E2
title: "Implement source adapter and fixture corpus"
status: proposed
revision: 1
actionable: false
priority: P0
size: M
milestone: M1
dependencies: [E1-T2]
requirement_ids: [P-006, P-007]
decision_ids: [ADR-006]
deferred_decision_ids: []
source: "legacy-roadmap:E2-T1"
promotion:
  status: not_promoted
  target: null
  promoted_by: null
  promoted_at: null
---

# E2-T1: Implement source adapter and fixture corpus

> This candidate is planning input only. It is not approved, scheduled, ready, or in progress.

## Outcome

Contribute the independently reviewable result described by **Implement source adapter and fixture corpus** to the epic outcome: deterministic extraction from the raw Telegram export with reconciled dry-run reporting.

## Original roadmap definition

The following definition preserves the original E2-T1 roadmap entry:

- Priority/size: P0 / M
- Dependencies: E1-T2
- Work:
  - Stream the Telegram Desktop JSON into the common `RawMessage` shape.
  - Support mixed text/entity encoding and source checksums.
  - Create synthetic/redacted fixtures for known message/media shapes.
- Acceptance:
  - The adapter processes the 21 MB JSON without whole-file loading.
  - Every input record is counted by type.
  - Tests cover string/mixed text, service, photo, video, reply, and malformed records.

## Scope and approval boundary

- Preserve the roadmap work and acceptance criteria above for refinement against the owner-approved spike.
- Do not treat this file, its priority, its branch note, or its roadmap ordering as permission to implement.
- Production code, scaffolds, migrations, infrastructure changes, and disposable proof code remain out of scope until promotion and current implementation-plan approval.

## Dependencies and traceability

- Task dependencies: [E1-T2](../../E1-repository-developer-foundation/proposed-tasks/E1-T2-scaffold-web-and-backend-applications.md)
- Milestone: [M1](../../../milestones/M1-vertical-proof.md).
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
