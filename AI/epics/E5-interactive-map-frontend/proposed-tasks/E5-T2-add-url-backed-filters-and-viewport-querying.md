---
schema: ai-workflow/proposed-task@1
id: E5-T2
epic: E5
title: "Add URL-backed filters and viewport querying"
status: proposed
revision: 1
actionable: false
priority: P0
size: L
milestone: M1
dependencies: [E5-T1, E4-T2]
requirement_ids: [P-001, P-003, P-004]
decision_ids: [ADR-002, ADR-003, ADR-012]
deferred_decision_ids: []
source: "legacy-roadmap:E5-T2"
promotion:
  status: not_promoted
  target: null
  promoted_by: null
  promoted_at: null
---

# E5-T2: Add URL-backed filters and viewport querying

> This candidate is planning input only. It is not approved, scheduled, ready, or in progress.

## Outcome

Contribute the independently reviewable result described by **Add URL-backed filters and viewport querying** to the epic outcome: a responsive, accessible map/list/detail experience over dated offers.

## Original roadmap definition

The following definition preserves the original E5-T2 roadmap entry:

- Priority/size: P0 / L
- Dependencies: E5-T1, E4-T2
- Work:
  - Implement all filters from [product requirements](../../../product/EXPERIENCE.md).
  - Serialize canonical filter state to URL.
  - Debounce/cancel viewport requests and preserve state through errors.
- Acceptance:
  - Reloading/shared URL restores identical filters.
  - Clear/reset behavior is deterministic.
  - Pins remain only when at least one offer matches.
  - Viewport requests are debounced, obsolete requests are cancelled, and loading/API errors do not clear filters.
  - M1 demonstrates at least price, room, and content-type filtering.

## Scope and approval boundary

- Preserve the roadmap work and acceptance criteria above for refinement against the owner-approved spike.
- Do not treat this file, its priority, its branch note, or its roadmap ordering as permission to implement.
- Production code, scaffolds, migrations, infrastructure changes, and disposable proof code remain out of scope until promotion and current implementation-plan approval.

## Dependencies and traceability

- Task dependencies: [E5-T1](E5-T1-build-map-shell-and-grouped-pin-interaction.md), [E4-T2](../../E4-read-api-filter-contracts/proposed-tasks/E4-T2-implement-facets-and-location-offer-collection.md)
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
