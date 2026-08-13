---
schema: ai-workflow/proposed-task@1
id: E3-T3
epic: E3
title: "Implement geocoder abstraction and cache"
status: proposed
revision: 1
actionable: false
priority: P0
size: L
milestone: M1
dependencies: [E3-T1, E2-T2]
requirement_ids: [P-001, P-007]
decision_ids: [ADR-005, ADR-012]
deferred_decision_ids: [D-002]
source: "legacy-roadmap:E3-T3"
promotion:
  status: not_promoted
  target: null
  promoted_by: null
  promoted_at: null
---

# E3-T3: Implement geocoder abstraction and cache

> This candidate is planning input only. It is not approved, scheduled, ready, or in progress.

## Outcome

Contribute the independently reviewable result described by **Implement geocoder abstraction and cache** to the epic outcome: idempotent canonical data and web-safe media with reviewed map coordinates.

## Original roadmap definition

The following definition preserves the original E3-T3 roadmap entry:

- Priority/size: P0 / L
- Dependencies: E3-T1, E2-T2
- Work:
  - Normalize addresses and district names.
  - Add provider-neutral result mapping, persistent cache, Warsaw bounds, confidence/precision, and review states.
  - Add a no-network fixture/cached provider for the vertical proof.
  - Add the policy-controlled one-time Nominatim seed adapter.
  - Evaluate the verified Warsaw fixture against Geoapify and LocationIQ per [geocoding documentation](../../../ingestion/GEOCODING.md); use Geoapify free as the initial default if quality passes.
- Acceptance:
  - Repeated queries hit the database cache.
  - Out-of-bounds/low-precision results cannot become accepted pins automatically.
  - Provider rate, identification, timeout, and retry policy is tested.
  - Hosted-provider attribution, quota exhaustion, secret handling, and fallback/defer behavior are tested.
  - M1 can resolve known fixtures with no external call.

## Scope and approval boundary

- Preserve the roadmap work and acceptance criteria above for refinement against the owner-approved spike.
- Do not treat this file, its priority, its branch note, or its roadmap ordering as permission to implement.
- Production code, scaffolds, migrations, infrastructure changes, and disposable proof code remain out of scope until promotion and current implementation-plan approval.

## Dependencies and traceability

- Task dependencies: [E3-T1](../tasks/E3-T1-create-schema-and-migrations.md), [E2-T2](../../E2-historical-export-parser-audit/proposed-tasks/E2-T2-implement-candidate-detection-and-typed-extractors.md)
- Deferred-decision gates: [D-002](../../../decisions/deferred/D-002-recurring-geocoding-provider.md).
- Milestone: [M1](../../../milestones/M1-vertical-proof.md).
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
