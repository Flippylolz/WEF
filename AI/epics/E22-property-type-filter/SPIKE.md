---
schema: ai-workflow/spike@1
epic: E22
title: "Property type classification and filter research"
status: approved
revision: 1
owner: owner
research_only: true
code_allowed: false
decision_ids:
  - ADR-005
  - ADR-006
  - ADR-012
  - ADR-013
domain_docs:
  - ../../product/EXPERIENCE.md
  - ../../contracts/DATA_MODEL.md
  - ../../contracts/HTTP_API.md
  - ../../contracts/OPENAPI.md
  - ../../ingestion/PIPELINE.md
  - ../../architecture/SYSTEM.md
proposed_task_ids:
  - E22-T1
  - E22-T2
  - E22-T3
approval:
  required_role: owner
  status: approved
  decided_by: "Flippylolz"
  decided_at: "2026-09-02T15:46:31Z"
  approved_revision: 1
  evidence: "Owner statement in Codex task on 2026-09-02: 'I approve E22 SPIKE.md revision 1.'"
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# Spike: Property type classification and filter research

## Question

How should the catalog represent, derive, backfill, expose, and filter Apartment,
House, and Semi-detached house without overloading existing fields or inventing
facts for ambiguous historical offers?

## Context and constraints

- `Offer.content_type` currently means offer granularity (`development` or
  `unit`); it is not the physical kind of property.
- `Offer.market_type` currently means `primary`, `secondary`, or `unknown`; it is
  unrelated to the requested property kind.
- `MapFilters` is the backend-owned filter object shared by grouped map,
  viewport-listing, and selected-location queries. Repeated values are OR within
  a group and groups are ANDed.
- `GET /api/v1/filter-facets` supplies canonical filter choices to the frontend.
  Frontend state is encoded as repeated query parameters and rendered from
  generated OpenAPI types.
- Existing offers have no reliable property-type column. A migration cannot assign
  apartment merely because an offer is an individual unit.
- Deterministic extraction retains exact source offsets and parser provenance.
  E17-T2 already provides replay/re-import infrastructure over retained source
  records.
- Public browsing remains available for records with incomplete structured data.
  Activating a property-type filter may exclude unknown values, but adding the
  field must not hide records by default or change visibility.
- The source corpus is multilingual and may use Polish, Russian, Ukrainian, or
  English terminology. Generic words such as “house/home/dom” can describe a
  building or marketing context rather than the offered property.
- This spike inspected current code and documentation only. It did not inspect or
  commit raw exports, call an external provider, or create executable artifacts.

## Evidence

- Verified: the canonical domain contains only `ContentType` and `MarketType` for
  the two existing categorical offer dimensions.
- Verified: database constraints allow only the current values and the main group
  index covers `content_type` and `market_type`; a new persisted dimension requires
  a forward migration and query-plan review.
- Verified: map, facets, location offers, and viewport listings reuse
  `SQLAlchemyMapQueryAdapter.filter_conditions`, so adding the predicate there is
  the reliable way to prevent map/list drift.
- Verified: the filter request model, normalized ETag key, facets projection,
  OpenAPI document, generated TypeScript types, URL parser/serializer, filter
  controls, filter chips, and clear behavior all enumerate categorical groups.
- Verified: deterministic listing extraction and persistence already carry
  field-level evidence into `OfferSource.extraction_json`; property type can use
  the same provenance boundary.
- Verified: a location may relate to many offers. Storing property type on
  `Location` would incorrectly force every offer at that place into one category.
- Assumption requiring owner confirmation: “house” means a standalone/detached
  house, and “blizhnyak” means Polish `bliźniak`, exposed in the API as
  `semi_detached`.
- Uncertainty: classification coverage and false-positive rates cannot be known
  from schema/code inspection. The implementation must measure a sanitized or
  production-safe replay report before the filter is promoted as complete.

## Options considered

1. **Add an offer-level `property_type` vocabulary (selected).** Use
   `apartment`, `house`, `semi_detached`, and internal/public `unknown`. This is
   semantically correct, additive, filterable, and supports safe legacy migration.
   It requires coordinated ingestion, schema, query, contract, and UI work.
2. **Extend `content_type` with the requested values (rejected).** Development vs
   unit describes the shape of a post, while apartment vs house describes the
   asset. Combining them would create invalid states, break existing URLs and
   contracts, and make development-level house offers impossible to represent.
3. **Infer property type only in the frontend (rejected).** The browser does not
   receive complete source evidence, cannot filter grouped SQL results correctly,
   and would duplicate business semantics outside the backend.
4. **Classify every historical offer with AI (deferred, not selected).** This may
   improve coverage, but it adds provider privacy, cost, validation, provenance,
   and production-activation concerns. Start with deterministic, evidence-backed
   classification and measure the remaining unknown cohort first.

## Recommendation

Add `PropertyType` to the catalog domain with stable values `apartment`, `house`,
`semi_detached`, and `unknown`. Persist it as a non-null offer column defaulting
legacy rows to `unknown`. Public filter input and facets allow only the three
requested classified choices, while offer projections may return `unknown` so the
UI can label incomplete records honestly.

Use a single deterministic classifier over complete source text. Match the most
specific semi-detached vocabulary before generic house vocabulary, attach exact
source spans, and return `unknown` plus a stable conflict warning when evidence
names different categories. Do not infer from numeric fields, photos, location,
development, or `content_type`.

Replay historical source revisions idempotently after the schema/parser release.
The operator report records total offers, classified counts by type, unknown
count, conflicts, changed rows, unchanged rows, failures, and parser version,
without raw source text. The replay must preserve offer identity, visibility,
location, dates, contacts, media, and unrelated field origins.

Extend the existing shared filter rather than create a separate endpoint. Requests
use repeated `property_type` values from the three-value filterable subset; values
combine with OR and the group combines with every other filter using AND. The same
normalized filters drive map pins, viewport results, selected-location matching,
and cache identity. A manual `property_type=unknown` request is rejected rather
than becoming an undocumented fourth filter choice.

Render three facets-driven checkboxes in the existing filter panel. No boxes
selected means no constraint. Show a summarized active chip and keep state in the
URL across reload/back/forward/share. Cards and details display the classified
value, including a neutral “Not classified” label for `unknown`.

## Proposed task boundaries

- **E22-T1 — Property classification and safe backfill:** domain enum, offer
  migration/check constraint, deterministic multilingual extraction with
  provenance/conflict behavior, persistence/replay integration, idempotent
  backfill report, data-quality fixtures, migration/replay tests, and operational
  rollback notes.
- **E22-T2 — Catalog property-type contracts:** shared filter group, SQL predicate,
  canonical facets, map/location/viewport consistency, offer summary/detail
  projections, normalized cache key, query-plan evidence/index decision, OpenAPI,
  generated types, and backend tests.
- **E22-T3 — Property-type filter UI:** URL state, API request mapping, accessible
  facets-driven controls, active chip/count/clear behavior, result/detail labels,
  loading/error preservation, responsive behavior, unit/accessibility/browser
  tests, and rollout verification.

## Risks and open questions

- **Terminology ambiguity:** owner approval of this revision confirms the meaning
  of House and Semi-detached house stated above. A different taxonomy returns the
  epic to this spike.
- **False generic-house matches:** use explicit property-bearing phrases, specific
  terms before generic terms, conflict-to-unknown behavior, and reviewed fixtures.
- **Low historical coverage:** report it; do not guess. A later AI or owner-curation
  workflow requires a new approved scope if deterministic coverage is inadequate.
- **Replay regression:** scope writes to `property_type` and its provenance only;
  assert all unrelated canonical fields and visibility are unchanged.
- **Map/list drift:** one `MapFilters` value and one shared SQL predicate set serve
  every public collection.
- **Query slowdown:** capture representative `EXPLAIN` evidence before adding an
  index; avoid speculative indexes.
- **URL compatibility:** the new parameter is additive; old URLs continue to mean
  no property-type constraint.

## Invalidation triggers

Return to the spike if the taxonomy expands, House should include semi-detached
homes, property type moves to Location/Development, classification uses an external
provider, unknown records should match active filters, or existing visibility/
availability semantics change. Return to the implementation plan for task order,
module, migration, test, rollout, or rollback changes within this recommendation.

## Exit checklist

- [x] The question is answered within the stated scope.
- [x] Evidence and uncertainty are distinguishable.
- [x] Affected decisions and domain documents are linked.
- [x] Proposed task boundaries and dependencies are identified.
- [x] No production or disposable proof code was created.
- [x] `revision` represents the material content being submitted.
- [x] `status` is `approved` and approval records revision 1.

## Owner decision

Flippylolz explicitly approved revision 1 in the Codex task on 2026-09-02. The
decision is recorded in the YAML `approval` object. It confirms the taxonomy and
semantics and permits task promotion plus implementation planning; it does not
permit implementation code.
