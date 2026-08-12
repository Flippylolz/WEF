---
schema: ai-workflow/spike@1
epic: E3
title: "Database, geocoding, and media pipeline research"
status: draft
revision: 1
owner: owner
research_only: true
code_allowed: false
decision_ids: [ADR-003, ADR-005, ADR-006, ADR-007, ADR-011, ADR-012, ADR-016]
domain_docs: [data, contracts, ingestion, security]
proposed_task_ids: [E3-T1, E3-T2, E3-T3, E3-T4, E3-T5]
approval:
  required_role: owner
  status: pending
  decided_by: null
  decided_at: null
  approved_revision: null
  evidence: null
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# Spike: Database, geocoding, and media pipeline

> This is a draft research scope. It authorizes documentation/research only: no production code, scaffold, migration, infrastructure/configuration change, generated executable artifact, prototype, proof branch, or disposable proof code.

## Question

What persisted model and bounded geocoding/media workflows make historical reprocessing idempotent, map coordinates reviewable, and public media paths safe on the single-host deployment?

## Context and constraints

- PostgreSQL/PostGIS is canonical; source identity, revisions, provenance, checkpoints, and ingest runs must survive reprocessing.
- No real-world availability boolean may be introduced.
- External geocoding uses a provider-neutral port, persistent cache, Warsaw bounds, confidence/precision, and review states; D-002 gates provider use.
- Media is copied atomically to opaque keys, served read-only, and stripped of unnecessary metadata; source paths never become public URLs.

Governing domains:

- [Data](../../data/README.md)
- [Contracts](../../contracts/README.md)
- [Ingestion](../../ingestion/README.md)
- [Security](../../security/README.md)

Governing decisions and deferred gates:

- [ADR-003](../../decisions/adr/ADR-003-do-not-infer-current-availability.md)
- [ADR-005](../../decisions/adr/ADR-005-postgresql-postgis.md)
- [ADR-006](../../decisions/adr/ADR-006-shared-ingestion-core.md)
- [ADR-007](../../decisions/adr/ADR-007-mounted-media-storage-interface.md)
- [ADR-011](../../decisions/adr/ADR-011-accounts-gate-contact-reveal.md)
- [ADR-012](../../decisions/adr/ADR-012-backend-centric-modular-monolith.md)
- [ADR-016](../../decisions/adr/ADR-016-pseudonymous-accounts-owner-console.md)
- [D-002](../../decisions/deferred/D-002-recurring-geocoding-provider.md)

## Research method

Review persisted contracts, ingestion/geocoding rules, source/media constraints, PostGIS indexing needs, provider policy, and single-host storage boundaries. Compare transaction and reprocessing boundaries in documentation only.

Research outputs must remain non-executable Markdown. Any data inspection must preserve source privacy and may not copy real source payload, contacts, credentials, sessions, or media into this artifact.

## Current evidence baseline

- ADR-005 selects PostgreSQL/PostGIS, ADR-007 selects mounted media behind a storage interface, and ADR-006 requires one ingestion core.
- The roadmap requires advisory locking, bounded transactions, resumable checkpoints, checksum deduplication, and migration tests.
- D-002 identifies Geoapify as the initial candidate, LocationIQ as an alternative, and public Nominatim as one-time cached seed use only.

These are planning facts and constraints, not evidence that implementation or acceptance checks have run.

## Options to evaluate

- Use canonical source/revision entities, idempotent upserts, narrow repository/UoW ports, cached provider-neutral geocoding, and local opaque media storage.
- Persist parser output directly into public projections, which would couple uncertainty and reprocessing to API shape.
- Expose source media paths or provider-specific fields, which would violate storage and contract boundaries.

## Draft recommendation

Refine schema/migration, persistence/reprocessing, geocoder/cache, media derivative, and complete-import tasks as separate reviewable boundaries with explicit reconciliation and recovery behavior.

This recommendation remains draft and may change after bounded research. It is not approved and does not authorize any proposed task.

## Proposed task boundaries

- [E3-T1: Create schema and migrations](proposed-tasks/E3-T1-create-schema-and-migrations.md) — candidate boundary for spike refinement.
- [E3-T2: Implement idempotent persistence and reprocessing](proposed-tasks/E3-T2-implement-idempotent-persistence-and-reprocessing.md) — candidate boundary for spike refinement.
- [E3-T3: Implement geocoder abstraction and cache](proposed-tasks/E3-T3-implement-geocoder-abstraction-and-cache.md) — candidate boundary for spike refinement.
- [E3-T4: Implement media storage and derivatives](proposed-tasks/E3-T4-implement-media-storage-and-derivatives.md) — candidate boundary for spike refinement.
- [E3-T5: Import and review the complete dataset](proposed-tasks/E3-T5-import-and-review-the-complete-dataset.md) — candidate boundary for spike refinement.

No candidate above may appear in an executable implementation-plan sequence while it remains under `proposed-tasks/`.

## Risks and open questions

- A uniqueness or transaction mistake can duplicate canonical offers or advance checkpoints before commit.
- Low-precision/out-of-bounds coordinates can become misleading public pins.
- Single-host media/database persistence is not backup; E7-T5 remains deferred.
- Confirm task-level traceability, cross-epic dependencies, test evidence, rollout, and rollback during spike refinement.
- Resolve every named deferred-decision gate before promoting affected work.

## Invalidation triggers

- A change to this epic's outcome, accepted architecture/dependency direction, public or persisted contracts, security model, ingestion semantics, or deployment topology.
- A new external dependency or service that changes data handling, operations, licensing, secrets, or replacement paths.
- Evidence that a listed task boundary cannot remain independently reviewable or that a roadmap dependency is incomplete.

## Exit checklist

- [ ] The bounded question is answered with evidence and uncertainty distinguished.
- [ ] Governing domain documents and decisions are reviewed and linked.
- [ ] Options, recommendation, risks, and open questions are complete.
- [ ] Proposed task scope, acceptance, dependencies, priority/size, and traceability are refined.
- [ ] No production or disposable proof code was created.
- [ ] `revision` represents the material content being submitted.
- [ ] Status is changed to `awaiting_approval` while approval remains `pending`.

## Owner decision

The owner records the decision only in the YAML `approval` object. Approval of the current spike revision would permit task refinement/promotion and implementation planning only; it would not permit code.
