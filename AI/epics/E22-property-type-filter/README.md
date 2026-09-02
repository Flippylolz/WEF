---
schema: ai-workflow/epic@1
id: E22
title: "Property type classification and filter"
status: ready
milestones: [M5]
owner: owner
spike: SPIKE.md
implementation_plan: IMPLEMENTATION_PLAN.md
---

# E22: Property type classification and filter

## Outcome

Visitors can narrow the Warsaw catalog by the physical kind of property:
**Apartment**, **House**, or **Semi-detached house (bliźniak)**. The selection is
shareable in the URL and consistently filters map pins, viewport results, and the
offers shown for a selected location.

## User problem

The existing filters distinguish a development post from an individual-unit post
and distinguish primary from secondary market. Neither field tells a visitor
whether the actual property is an apartment, a standalone house, or one half of a
semi-detached house. Visitors must currently open and read individual offers to
make that distinction.

## User story

As a buyer browsing Warsaw properties, I want to select one or more property
types so that every visible pin and result contains an offer of the kind of home I
am considering.

## Terminology and product rules

- Stable values are `apartment`, `house`, and `semi_detached`.
- **House** means a standalone/detached house. It does not include a
  semi-detached house.
- **Semi-detached house** is the English UI label for Polish `bliźniak` (the
  requested “blizhnyak” category).
- The values are mutually exclusive per offer, but visitors may select multiple
  values. Selected values combine with OR; this group combines with every other
  active filter using AND.
- No selection means all property types, including offers not yet classified.
- An active selection excludes unclassified offers. The system does not infer a
  property type when the source evidence is ambiguous.
- Property type belongs to an offer, not a location: one location or development
  can contain offers for different physical property types.

## Scope

- Add a canonical backend property-type vocabulary plus an explicit `unknown`
  persistence value for legacy and ambiguous offers.
- Extract high-confidence property type from source descriptions with exact
  provenance, conflict handling, parser replay, and a bounded coverage report.
- Add the property-type group to the shared map filters, canonical facets,
  location-offer results, viewport listings, offer summaries, and offer details.
- Add an accessible, facets-driven filter control, active-filter chip, clear/reset
  behavior, and repeated `property_type` URL parameters.
- Backfill historical offers idempotently without changing visibility, location,
  publication time, or availability semantics.

## Out of scope

- Rental/sale transaction type, commercial-property categories, plots, terraced
  houses, farmhouses, or a general-purpose property taxonomy.
- Guessing from price, area, room count, location, photos, or development name.
- Treating `content_type=unit` as equivalent to apartment.
- Reclassifying ambiguous offers automatically through an external AI provider.
- Changing offer visibility or claiming current availability.
- Polish interface localization; `bliźniak` is included as terminology support in
  the English label and source classifier.

## Epic acceptance

- A visitor can select Apartment, House, Semi-detached house, or any combination,
  and the map, list, and selected-location offers agree.
- The URL round-trips the selection across reload, back/forward navigation, and a
  shared link.
- Unknown or ambiguous offers remain visible with no active property-type filter
  and do not match an active property-type filter.
- New and replayed source records use one canonical classifier with exact evidence
  and deterministic conflict behavior.
- Existing rows migrate safely to `unknown`; the backfill is idempotent, measured,
  and does not alter visibility or unrelated canonical values.
- OpenAPI, generated frontend types, backend integration tests, frontend unit and
  accessibility tests, and the critical browser journey cover the new group.
- Representative filtered queries remain within the existing catalog performance
  budget and use a reviewed index only when query-plan evidence justifies it.

## Planning state

- [Spike revision 1](SPIKE.md) is owner-approved.
- [Implementation plan revision 2](IMPLEMENTATION_PLAN.md) is owner-approved.
- E22-T1 is `ready`; E22-T2 and E22-T3 remain `draft` behind their task
  dependencies:
  - [E22-T1 — Add canonical property classification and safe
    backfill](tasks/E22-T1-property-classification-and-backfill.md)
  - [E22-T2 — Extend catalog filter and public contracts](tasks/E22-T2-catalog-property-type-contracts.md)
  - [E22-T3 — Add the URL-backed property type filter UI](tasks/E22-T3-property-type-filter-ui.md)

## Dependencies

- E22-T1 builds on the completed raw replay and parser-provenance path in E17-T2.
- E22-T2 builds on E22-T1 and the completed shared filter/query contracts in
  E4-T4.
- E22-T3 builds on E22-T2 and the completed map/list experience in E13-T3.

No implementation is authorized until the repository's spike, promotion,
implementation-plan, dependency, and dedicated-branch gates are satisfied.
