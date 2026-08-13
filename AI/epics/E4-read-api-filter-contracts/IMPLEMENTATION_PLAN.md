---
schema: ai-workflow/implementation-plan@1
epic: E4
title: "M1 grouped map API implementation plan"
status: approved
revision: 2
owner: owner
spike_revision: 2
task_sequence:
  - id: E4-T1
    revision: 2
  - id: E4-T2
    revision: 2
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

# Implementation Plan: M1 grouped map API

## Approved spike baseline

[E4 spike revision 2](SPIKE.md) approves grouped GeoJSON/filter, canonical facets, and the selected-location dated-offer collection. Details, media, auth, contacts, and full-data hardening remain proposed.

## Scope and outcome

Replace the public list proof with stable backend-owned map/facet/selected-location contracts over E3's migrated synthetic M1 records. One filter policy is reused across compact GeoJSON, canonical options, and dated results.

## Ordered task sequence

### 1. E4-T1 — Implement map query service and GeoJSON endpoint

- Task: [E4-T1 revision 2](tasks/E4-T1-implement-map-query-service-and-geojson-endpoint.md).
- Dependency: E3-T1 must become a direct ancestor PR or complete before this task starts.
- Independent result: API/query/contract changes remain reviewable separately from schema and UI.
- Affected code: map application/domain/interface/infrastructure modules, composition, OpenAPI/generated client, tests.
- Verification: unit/PostGIS/contract/security/performance/same-origin smoke.

### 2. E4-T2 — Implement facets and location offer collection

- Task: [E4-T2 revision 2](tasks/E4-T2-implement-facets-and-location-offer-collection.md).
- Dependency: E4-T1 must become its direct ancestor PR or complete before start.
- Independent result: adds options/result-panel data without mixing frontend work into backend review.
- Affected code: shared filter policy plus facet/collection ports, adapters, presenters, routes, OpenAPI/types, tests.
- Verification: aggregation, cursor tie cases, matching/history behavior, safe IDs/cursors, contract and Caddy smoke.

## Cross-task architecture

Pydantic query input maps into application-owned immutable filters. Query services invoke narrow inward-owned ports. SQLAlchemy/PostGIS implements filtering/grouping/aggregation/pagination. Pure presenters create versioned responses. Routes contain transport behavior only. E4-T2 imports/reuses E4-T1 application policy rather than copying semantics.

## Data and migrations

No migration is added. The query relies on E3-T1's locations/offers/indexes and accepted synthetic points. E3-T3 remains required before real unresolved addresses become public.

## Security and privacy

The public response is an explicit allowlist. It excludes source/raw text, contacts, paths, media internals, provider responses, and credentials. Input bounds/count/range limits prevent unbounded spatial queries. Logs record safe metadata, not query/source values.

## Test and verification strategy

- Unit tests for normalized filters and pure presenter.
- PostGIS integration matrix for all filter semantics/group counts/scope/order.
- OpenAPI generation, generated TypeScript, docs lint/build, and breaking-change probe for all three endpoints.
- Cursor/facet/location integration matrices and selected-location same-origin flow.
- Conditional ETag tests, safe problem responses, and representative local query timing.
- Local Caddy endpoint smoke against E3 seed.

## Operations, rollout, and rollback

Activate after E3 migration/seed. Keep health routes stable. Application rollback requires only E3 schema compatibility. No schema/data/provider operation occurs in E4-T1.

## Risks and mitigations

- **Semantic duplication:** one application filter policy and one query adapter.
- **Coordinate reversal:** integration and contract assertions.
- **Filter explosion:** validated counts/ranges/bbox.
- **Stale cache:** deterministic ETag tied to normalized filters plus latest relevant data version.
- **Real low-confidence pin:** persistence predicate requires accepted/in-scope/non-null coordinates.
- **Map/collection drift:** shared filter object and paired integration assertions.
- **Cursor gaps:** deterministic timestamp/UUID order and tie fixtures.

## Invalidation triggers

Return to the spike for a different public map representation, server-side tiles, real-source visibility bypass, or frontend-owned filtering. Return to this plan for material endpoint/query/test/rollout changes within the approved architecture.

## Approval checklist

- [x] E4 spike revision 2 is explicitly approved/current.
- [x] E4-T1/T2 revision 2 are promoted with complete acceptance/traceability.
- [x] Dependencies on E3-T1 and ordered E4-T1 ancestry are acyclic/start-gated.
- [x] Modules, contract, tests, risks, rollout, and rollback are explicit.
- [x] No deferred decision blocks the synthetic map API.
- [x] No implementation code was written before this plan approval.
- [x] Revision 2 records the approved plan.

## Owner decision

Flippylolz approved revision 2 through the delegated overnight MVP/autodeploy directive. E4-T1 starts after E3-T1 ancestry and E4-T2 after E4-T1 ancestry; this does not authorize details/media/auth/contacts or real-source publication.
