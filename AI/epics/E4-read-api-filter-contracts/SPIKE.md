---
schema: ai-workflow/spike@1
epic: E4
title: "Read API and filter contracts research"
status: draft
revision: 1
owner: owner
research_only: true
code_allowed: false
decision_ids: [ADR-002, ADR-003, ADR-005, ADR-007, ADR-011, ADR-012, ADR-013, ADR-016]
domain_docs: [product, contracts, architecture, security]
proposed_task_ids: [E4-T1, E4-T2, E4-T3, E4-T4]
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

# Spike: Read API and filter contracts

> This is a draft research scope. It authorizes documentation/research only: no production code, scaffold, migration, infrastructure/configuration change, generated executable artifact, prototype, proof branch, or disposable proof code.

## Question

How should the backend express map, facet, collection, detail, error, caching, and performance contracts so filter semantics and masking are implemented once and consumed through generated types?

## Context and constraints

- The backend owns visibility, inclusive range overlap, null behavior, AND/OR semantics, grouping, sorting, facets, pagination, links, permissions, and masking.
- Map responses are compact GeoJSON with matching/total counts and source dates, not full details or media arrays.
- FastAPI OpenAPI is deterministic and committed; production OpenAPI/Swagger/ReDoc routes remain disabled.
- Public responses expose no raw payload, local path, dedicated raw contact field, or unverified Telegram link.

Governing domains:

- [Product](../../product/README.md)
- [Contracts](../../contracts/README.md)
- [Architecture](../../architecture/README.md)
- [Security](../../security/README.md)

Governing decisions and deferred gates:

- [ADR-002](../../decisions/adr/ADR-002-grouped-location-development-map.md)
- [ADR-003](../../decisions/adr/ADR-003-do-not-infer-current-availability.md)
- [ADR-005](../../decisions/adr/ADR-005-postgresql-postgis.md)
- [ADR-007](../../decisions/adr/ADR-007-mounted-media-storage-interface.md)
- [ADR-011](../../decisions/adr/ADR-011-accounts-gate-contact-reveal.md)
- [ADR-012](../../decisions/adr/ADR-012-backend-centric-modular-monolith.md)
- [ADR-013](../../decisions/adr/ADR-013-committed-openapi-offline-docs.md)
- [ADR-016](../../decisions/adr/ADR-016-pseudonymous-accounts-owner-console.md)

## Research method

Trace product P-001 through P-008 against data/HTTP/OpenAPI contracts, query-service boundaries, presenter responsibilities, PostGIS query plans, cache/ETag behavior, and abuse/error limits.

Research outputs must remain non-executable Markdown. Any data inspection must preserve source privacy and may not copy real source payload, contacts, credentials, sessions, or media into this artifact.

## Current evidence baseline

- P-001/P-003 define grouped pins and filter semantics; P-002/P-005/P-006/P-007/P-008 constrain detail, media, links, trust, and contacts.
- ADR-012 assigns read projections to backend query services and transport serialization to presenters.
- The roadmap targets 500 ms p95 for a representative Warsaw map query and requires deterministic cursor pagination.

These are planning facts and constraints, not evidence that implementation or acceptance checks have run.

## Options to evaluate

- Use dedicated application query contracts with optimized PostGIS adapters and versioned presenters/OpenAPI schemas.
- Return ORM entities for frontend filtering/grouping, which duplicates rules and leaks persistence shape.
- Create separate map/list filter implementations, which risks semantic drift.

## Draft recommendation

Keep one backend filter/query policy shared by grouped map, facets, location collections, and detail capabilities; verify it through integration, OpenAPI, generated-client, compatibility, and representative performance tests.

This recommendation remains draft and may change after bounded research. It is not approved and does not authorize any proposed task.

## Proposed task boundaries

- [E4-T1: Implement map query service and GeoJSON endpoint](proposed-tasks/E4-T1-implement-map-query-service-and-geojson-endpoint.md) — candidate boundary for spike refinement.
- [E4-T2: Implement facets and location offer collection](proposed-tasks/E4-T2-implement-facets-and-location-offer-collection.md) — candidate boundary for spike refinement.
- [E4-T3: Implement offer detail](proposed-tasks/E4-T3-implement-offer-detail.md) — candidate boundary for spike refinement.
- [E4-T4: Harden API behavior and performance](proposed-tasks/E4-T4-harden-api-behavior-and-performance.md) — candidate boundary for spike refinement.

No candidate above may appear in an executable implementation-plan sequence while it remains under `proposed-tasks/`.

## Risks and open questions

- Map and collection endpoints can diverge on null/range/filter semantics.
- Cursor ordering can omit or duplicate offers under ties.
- Caching or logs can retain sensitive source/contact content if envelopes are not constrained.
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
