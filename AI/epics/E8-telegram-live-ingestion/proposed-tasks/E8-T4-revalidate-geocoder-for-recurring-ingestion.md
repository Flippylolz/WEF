---
schema: ai-workflow/proposed-task@1
id: E8-T4
epic: E8
title: "Revalidate geocoder for recurring ingestion"
status: proposed
revision: 1
actionable: false
priority: P2
size: M
milestone: M4
dependencies: [E3-T3]
requirement_ids: [P-001, P-007]
decision_ids: [ADR-005, ADR-006]
deferred_decision_ids: [D-002]
source: "legacy-roadmap:E8-T4"
promotion:
  status: not_promoted
  target: null
  promoted_by: null
  promoted_at: null
---

# E8-T4: Revalidate geocoder for recurring ingestion

> This candidate is planning input only. It is not approved, scheduled, ready, or in progress.

## Outcome

Contribute the independently reviewable result described by **Revalidate geocoder for recurring ingestion** to the epic outcome: new, edited, and deleted channel posts are processed safely without changing public contracts.

## Original roadmap definition

The following definition preserves the original E8-T4 roadmap entry:

- Priority/size: P2 / M
- Dependencies: D-002, E3-T3
- Work:
  - Recheck the E3-T3 selected provider's current free quota/terms, quality, reliability, attribution, and expected live volume; retain it or migrate through the existing provider interface.
  - Define quota/rate/error monitoring and fallback/defer behavior for the always-on worker.
- Acceptance:
  - No live job depends on public Nominatim recurring use.
  - Cache, precision, bounds, retry, and review semantics remain provider-independent.
  - Provider credentials/attribution and quota-exhaustion behavior are production-tested.

## Scope and approval boundary

- Preserve the roadmap work and acceptance criteria above for refinement against the owner-approved spike.
- Do not treat this file, its priority, its branch note, or its roadmap ordering as permission to implement.
- Production code, scaffolds, migrations, infrastructure changes, and disposable proof code remain out of scope until promotion and current implementation-plan approval.

## Dependencies and traceability

- Task dependencies: [E3-T3](../../E3-database-geocoding-media/proposed-tasks/E3-T3-implement-geocoder-abstraction-and-cache.md)
- Deferred-decision gates: [D-002](../../../decisions/deferred/D-002-recurring-geocoding-provider.md).
- Milestone: [M4](../../../milestones/M4-live-telegram-updates.md).
- Traceability: [Product requirements](../../../product/EXPERIENCE.md), [Decision registry](../../../decisions/README.md), [Ingestion](../../../ingestion/README.md), [Data](../../../data/README.md), [Operations](../../../operations/README.md), [Security](../../../security/README.md).

## Risks and notes

- Material changes to scope, dependencies, acceptance, contracts, security, ingestion, deployment, or rollback require workflow revalidation and approval.
- The exact roadmap priority/size is `P2 / M`.
- This task definition is authoritative only in this `proposed-tasks/` location until a valid promotion moves it to `tasks/`.

## Promotion checklist

- [ ] The epic spike is explicitly owner-approved for its current revision.
- [ ] Scope, acceptance criteria, dependencies, priority, size, and traceability have been reviewed against that spike.
- [ ] Required deferred decisions and milestone prerequisites are resolved.
- [ ] The file will be moved—not copied—to `tasks/` and converted to `ai-workflow/task@1`.
- [ ] Promotion metadata will identify the target, promoter, and timestamp.
