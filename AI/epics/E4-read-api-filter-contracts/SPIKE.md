---
schema: ai-workflow/spike@1
epic: E4
title: "Read API and filter contracts research"
status: approved
revision: 2
owner: owner
research_only: true
code_allowed: false
decision_ids: [ADR-002, ADR-003, ADR-005, ADR-007, ADR-011, ADR-012, ADR-013, ADR-016]
domain_docs: [product, contracts, architecture, security]
proposed_task_ids: [E4-T1, E4-T2, E4-T3, E4-T4]
approval:
  required_role: owner
  status: approved
  decided_by: Flippylolz
  decided_at: "2026-08-12T22:34:40Z"
  approved_revision: 2
  evidence: "Owner directive to prepare the MVP/autodeploy, choose safe defaults, log decisions/blockers, and continue stacking PRs"
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# Spike: Read API and filter contracts

> Revision 2 is approved research. The spike remains non-executable; implementation requires its approved plan and promoted task.

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

## Evidence

- P-001/P-003 define grouped pins and filter semantics; P-002/P-005/P-006/P-007/P-008 constrain detail, media, links, trust, and contacts.
- ADR-012 assigns read projections to backend query services and transport serialization to presenters.
- The roadmap targets 500 ms p95 for a representative Warsaw map query and requires deterministic cursor pagination.
- E0 proves the route/application-port/SQLAlchemy-adapter/presenter/OpenAPI/generated-client flow.
- E3 spike revision 2 provides accepted deterministic synthetic coordinates and dated offers without a geocoder provider.
- The first browser-visible endpoint needs grouped GeoJSON and all M1 filter semantics, but not facets, offer details, media, auth, or contact reveal.

No private source data is needed to verify this contract.

## Options to evaluate

- Use dedicated application query contracts with optimized PostGIS adapters and versioned presenters/OpenAPI schemas.
- Return ORM entities for frontend filtering/grouping, which duplicates rules and leaks persistence shape.
- Create separate map/list filter implementations, which risks semantic drift.

## Approved recommendation

Promote E4-T1 and E4-T2. E4-T1 implements a backend-owned filter value object and grouped map query service behind a narrow port, a SQLAlchemy/PostGIS adapter, and a pure GeoJSON presenter at `GET /api/v1/map/locations`. E4-T2 reuses that policy for canonical facets and the selected-location dated-offer collection needed by the clickable MVP.

For the synthetic MVP, E3-T1 is sufficient because its fixture coordinates are explicit accepted facts. E3-T3 remains mandatory before non-fixture addresses can become public pins. E4-T3 and E4-T4 remain proposed.

## Proposed task boundaries

- [E4-T1: Implement map query service and GeoJSON endpoint](tasks/E4-T1-implement-map-query-service-and-geojson-endpoint.md) — promote for M1.
- [E4-T2: Implement facets and location offer collection](tasks/E4-T2-implement-facets-and-location-offer-collection.md) — promote as the E4-T1 child needed by the M1 filter/result panel.
- [E4-T3: Implement offer detail](tasks/E4-T3-implement-offer-detail.md) — promoted; implementation in progress on PR #78.
- [E4-T4: Harden API behavior and performance](proposed-tasks/E4-T4-harden-api-behavior-and-performance.md) — keep proposed.

Only promoted E4-T1 and E4-T2 may appear in implementation-plan revision 2.

## Risks and open questions

- Map and collection endpoints can diverge on null/range/filter semantics.
- Cursor ordering can omit or duplicate offers under ties.
- Caching or logs can retain sensitive source/contact content if envelopes are not constrained.
- Query plans can regress; require a representative synthetic `EXPLAIN`/latency budget without treating local timing as production evidence.
- ETag correctness can hide updates; derive it from normalized filters and a deterministic data-version aggregate and test conditional requests.
- Real/non-fixture locations remain hidden until the separately approved geocoding/review path exists.

## Invalidation triggers

- A change to this epic's outcome, accepted architecture/dependency direction, public or persisted contracts, security model, ingestion semantics, or deployment topology.
- A new external dependency or service that changes data handling, operations, licensing, secrets, or replacement paths.
- Evidence that a listed task boundary cannot remain independently reviewable or that a roadmap dependency is incomplete.

## Exit checklist

- [x] The bounded question is answered with evidence and uncertainty distinguished.
- [x] Governing domain documents and decisions are reviewed and linked.
- [x] Options, recommendation, risks, and open questions are complete.
- [x] E4-T1/T2 scope, acceptance, dependencies, priority/size, and traceability are refined.
- [x] No production or disposable proof code was created during the spike.
- [x] Revision 2 represents the approved material content.
- [x] Status and approval metadata record the delegated owner decision.

## Owner decision

Flippylolz approved revision 2 through the explicit overnight MVP/autodeploy delegation. This permits E4-T1/T2 promotion and planning only; code still requires approved plan revision 2 and started task branches.
