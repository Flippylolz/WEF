---
schema: ai-workflow/proposed-task@1
id: E2-T2
epic: E2
title: "Implement candidate detection and typed extractors"
status: proposed
revision: 1
actionable: false
priority: P0
size: L
milestone: M1
dependencies: [E2-T1]
requirement_ids: [P-002, P-003, P-007]
decision_ids: [ADR-003, ADR-006, ADR-012]
deferred_decision_ids: []
source: "legacy-roadmap:E2-T2"
promotion:
  status: not_promoted
  target: null
  promoted_by: null
  promoted_at: null
---

# E2-T2: Implement candidate detection and typed extractors

> This candidate is planning input only. It is not approved, scheduled, ready, or in progress.

## Outcome

Contribute the independently reviewable result described by **Implement candidate detection and typed extractors** to the epic outcome: deterministic extraction from the raw Telegram export with reconciled dry-run reporting.

## Original roadmap definition

The following definition preserves the original E2-T2 roadmap entry:

- Priority/size: P0 / L
- Dependencies: E2-T1
- Work:
  - Add versioned rules for development and unit templates.
  - Extract market/content type, location, price, area, rooms, floor, delivery, development name, and map link.
  - Store source spans, confidence, and warnings.
- Acceptance:
  - Golden fixtures produce expected typed ranges and provenance.
  - Unknown/conflicting values remain null or reviewable, never invented.
  - Negative fixtures do not become offers.

## Scope and approval boundary

- Preserve the roadmap work and acceptance criteria above for refinement against the owner-approved spike.
- Do not treat this file, its priority, its branch note, or its roadmap ordering as permission to implement.
- Production code, scaffolds, migrations, infrastructure changes, and disposable proof code remain out of scope until promotion and current implementation-plan approval.

## Dependencies and traceability

- Task dependencies: [E2-T1](../tasks/E2-T1-implement-source-adapter-and-fixture-corpus.md)
- Milestone: [M1](../../../milestones/M1-vertical-proof.md).
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
