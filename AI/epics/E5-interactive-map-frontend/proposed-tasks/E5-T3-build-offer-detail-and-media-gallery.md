---
schema: ai-workflow/proposed-task@1
id: E5-T3
epic: E5
title: "Build offer detail and media gallery"
status: proposed
revision: 1
actionable: false
priority: P0
size: L
milestone: M3
dependencies: [E4-T3, E5-T1]
requirement_ids: [P-002, P-005, P-006, P-007]
decision_ids: [ADR-003, ADR-004, ADR-007, ADR-012]
deferred_decision_ids: []
source: "legacy-roadmap:E5-T3"
promotion:
  status: not_promoted
  target: null
  promoted_by: null
  promoted_at: null
---

# E5-T3: Build offer detail and media gallery

> This candidate is planning input only. It is not approved, scheduled, ready, or in progress.

## Outcome

Contribute the independently reviewable result described by **Build offer detail and media gallery** to the epic outcome: a responsive, accessible map/list/detail experience over dated offers.

## Original roadmap definition

The following definition preserves the original E5-T3 roadmap entry:

- Priority/size: P0 / L
- Dependencies: E4-T3, E5-T1
- Work:
  - Show typed fields, server-masked source text, publication date, history, confidence, and responsive gallery/video.
  - Show Telegram action only for verified URLs.
- Acceptance:
  - Publication date is prominent and no unsupported availability copy appears.
  - The drawer states when additional non-matching related posts exist.
  - Gallery is lazy-loaded and keyboard accessible, images have useful alternative text, and videos use accessible native controls.
  - Missing field/media/link states use clear placeholders and remain non-breaking.
  - Parsed/inferred low-confidence fields are identified.

## Scope and approval boundary

- Preserve the roadmap work and acceptance criteria above for refinement against the owner-approved spike.
- Do not treat this file, its priority, its branch note, or its roadmap ordering as permission to implement.
- Production code, scaffolds, migrations, infrastructure changes, and disposable proof code remain out of scope until promotion and current implementation-plan approval.

## Dependencies and traceability

- Task dependencies: [E4-T3](../../E4-read-api-filter-contracts/proposed-tasks/E4-T3-implement-offer-detail.md), [E5-T1](E5-T1-build-map-shell-and-grouped-pin-interaction.md)
- Milestone: [M3](../../../milestones/M3-public-dockerized-mvp.md).
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
