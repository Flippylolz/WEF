---
schema: ai-workflow/spike@1
epic: E13
title: "Dark map-first listing explorer"
status: awaiting_approval
revision: 1
owner: owner
research_only: true
code_allowed: false
decision_ids: [ADR-002, ADR-003, ADR-004, ADR-012, ADR-013]
domain_docs:
  - ../../product/EXPERIENCE.md
  - ../../product/QUALITY.md
  - ../../architecture/README.md
  - UX_DESIGN.md
proposed_task_ids: [E13-T1, E13-T2, E13-T3]
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

# Spike: Dark map-first listing explorer

## Question

How should the current Warsaw Estate Finder be redesigned into a dark,
Google-Maps-inspired discovery interface with selectable listings in a sidebar,
without moving catalog semantics into the frontend or regressing map/list
accessibility, URL-backed filters, detail/media behavior, and degraded-map use?

## Context and constraints

- The live production page at `https://2fa54e2405.duckdns.org/` was reviewed on
  2026-08-26 at desktop width together with the current E5 implementation.
- P-004 already requires a desktop map/results composition, mobile map-first
  sheet/full-list modes, map/list highlighting, viewport queries, and preserved
  filter state.
- ADR-002 keeps the grouped location/development model. ADR-003 prohibits copy
  that implies current availability. ADR-004 retains MapLibre/OpenFreeMap and
  visible attribution.
- Backend responses remain authoritative for filtering, visibility,
  confidence, prices, pagination, capabilities, and public-safe text. Generated
  OpenAPI types remain the frontend contract boundary.
- No production dependency, remote font, secret tile key, new map vendor, or
  private source data is introduced.
- This spike is documentation/research only. It does not create production
  code, an executable prototype, a generated contract, a migration, or an
  implementation plan.

## Research method

1. Inspect the live desktop page after catalog and facet loading.
2. Review `page.tsx`, `map-explorer.tsx`, `map-filter-controls.tsx`,
   `warsaw-map.tsx`, shared CSS, English messages, current product requirements,
   and the completed E5 interaction task.
3. Trace what can be composed from existing location-map and selected-location
   offer contracts, and identify where the requested listing rail requires a
   backend projection rather than frontend joins.
4. Compare three interaction models against result visibility, selection
   clarity, accessibility, responsive behavior, contract ownership, and
   rollout risk.

Prohibited before implementation-plan approval:

- production or application code;
- scaffolds, migrations, infrastructure/configuration changes, or generated
  executable artifacts;
- throwaway scripts, prototypes, proof branches, or disposable proof code.

## Evidence

### Verified live-product findings

- The desktop composition is a centered marketing page followed by a bounded
  map card. The large title/subtitle consume high-value vertical space before
  the search experience begins.
- The right rail puts the complete filter form before results. Price, area,
  rooms, districts, market, offer type, and date controls occupy the initially
  visible rail; the actual result collection begins below them.
- The current live viewport reported 776 grouped locations. Every location is
  rendered in one semantic list. Selected-location offers are appended after
  that full list, so the selected content can be hundreds of rows away from the
  control that opened it.
- The rail contains grouped locations, not offer/listing summaries. A location
  response has name, address, confidence, and matching-offer count. Offer
  summaries are fetched only after selecting one location.
- The live facet response displayed 19 district values and several visibly
  malformed or inconsistently cased values. Dark styling cannot fix this data
  normalization defect; the redesign must tolerate it and the defect should be
  handled independently by the backend/data owner.
- Map attribution is rendered both by MapLibre and by a custom page overlay.
  The duplicate consumes space and weakens visual hierarchy.
- Account actions float at the viewport edge independently of the page header.
  Selection and filter controls use several unrelated visual treatments.

### Verified code constraints

- List focus/hover already drives map highlight, and map selection drives the
  selected location state. This interaction can be preserved.
- List selection does not currently recenter the map. Selected and highlighted
  rings are layered on the existing point only.
- The map instance is intentionally stable across filter and selection changes;
  a redesign should not remount it.
- URL state already owns filters and viewport. A new layout should compose the
  existing codec rather than introduce a second filter store.
- The current map contract cannot render a useful offer card for every visible
  result without fetching offers location-by-location. That N+1 approach would
  be slow, wasteful, and inconsistent with backend-owned pagination.

### Assumptions and uncertainty

- In this design, **listing** means a dated offer, while **location** means the
  grouped pin/development entity already defined by ADR-002.
- If the owner instead intends the sidebar to contain only grouped locations,
  E13-T2 can be removed after spike approval and E13-T3 can use the existing map
  contract. That is cheaper, but provides much less property context than the
  requested Google Maps-style listing browser.
- The exact dark OpenFreeMap style URL and its production reliability must be
  verified during implementation planning; no vendor or URL is selected by
  this spike.

## Options considered

### Option A: Theme the current right rail

Change colors, preserve the current document structure, and restyle location
buttons.

- Benefits: smallest code diff; no contract work.
- Costs: filters still hide results; selected offers remain after the complete
  location list; the page still feels like a map embedded in a form.
- Decision: reject. It does not solve the core navigation problem.

### Option B: Left rail with grouped-location cards only

Move the existing location list to a persistent left rail, place filters in a
compact popover/drawer, and replace the list with selected-location offers on
selection.

- Benefits: frontend-only; works with existing generated contracts; removes
  the most severe selected-content placement issue.
- Costs: cards cannot show representative price, rooms, area, date, or media;
  users still select a place before seeing actual listings.
- Decision: keep as an independently shippable first slice and rollback-safe
  fallback, but not the complete requested outcome.

### Option C: Left rail with paginated offer cards and grouped map pins

Keep grouped location pins on the map while a backend viewport projection
returns paginated, filter-matching offer summaries for the rail. Selecting a
card highlights and recenters its parent location, then opens the existing
detail boundary.

- Benefits: matches the user mental model; supports compact, informative cards;
  avoids N+1 requests; lets backend own sorting, pagination, and safe fields.
- Costs: adds one contract/backend slice before the final frontend slice;
  requires explicit reconciliation between offer cards and grouped pins.
- Decision: recommend.

## Recommendation

Adopt Option C through three reviewable slices, with Option B delivered first
so visual and layout improvements do not wait on a new contract.

The target composition is:

- a compact 56–64 px dark application bar;
- a persistent 22–26 rem left discovery rail on desktop and a map-first bottom
  sheet/full-list flow on mobile;
- a search field and horizontal filter chips at the top of the rail, with the
  full filter form in an accessible drawer;
- a visible result count/sort row followed immediately by virtualized or
  paginated cards;
- a full remaining-width dark map with one attribution treatment;
- selected card and selected pin using the same high-contrast accent and a
  non-color selected state;
- a list → selected location/offer transition inside the rail, with an explicit
  Back to results control, rather than appending selected content after all
  results;
- a detail drawer only for the complete offer record/media/contact flow.

The design tokens, layouts, states, and interaction contract are defined in
[UX_DESIGN.md](UX_DESIGN.md).

No new ADR is required if MapLibre/OpenFreeMap and existing backend ownership
remain unchanged. A vendor or public-contract strategy departure would require
a decision record and spike revision.

## Proposed task boundaries

### E13-T1 — Build dark shell and compact filter experience

- Frontend-only visual/layout slice using existing contracts.
- Move discovery controls into the left rail; keep results immediately visible;
  implement dark tokens, dark map styling, one attribution surface, responsive
  shell, and filter drawer/chips.
- Preserve URL filters, map lifecycle, current selection semantics, auth,
  favorites, loading/error/empty states, and WCAG 2.2 AA.

### E13-T2 — Add viewport listing-summary projection

- Backend/OpenAPI/generated-client slice.
- Return paginated filter-matching offer cards keyed to parent location and
  current viewport, with only already-approved public-safe summary fields.
- Define deterministic sort/cursor behavior, bounds, query limits, and
  compatibility with grouped pin counts.

### E13-T3 — Build selectable listing rail and coordinated map behavior

- Frontend integration slice over E13-T1 and E13-T2.
- Render paginated/virtualized offer cards; synchronize hover/focus/selection
  with the grouped pin; recenter without remounting; preserve keyboard, mobile,
  loading, empty, error, degraded-map, and detail-focus behavior.

## Risks and open questions

- **Meaning of listing:** owner confirmation is required that offer cards, not
  grouped-location cards, are the desired primary result unit.
- **Sorting:** recommend newest publication first initially, with no invented
  relevance or availability score. Final sort semantics belong to E13-T2.
- **Map style availability:** verify a production-safe dark OpenFreeMap style
  and a readable light fallback before implementation approval.
- **Scale:** 776 locations in one rendered list is already too large for a
  polished rail. Pagination is required for offer cards; virtualization may be
  added only if measured DOM cost still warrants it.
- **Data quality:** malformed district facets and location text can dominate a
  compact UI. Treat normalization as a separate data-quality defect; do not
  silently correct or hide backend values in the frontend.
- **Selection continuity:** a selected offer may fall outside a changed filter
  or viewport. Preserve the selected snapshot long enough to explain the state,
  then provide Back to results rather than silently changing selection.

## Invalidation triggers

- The owner defines listing as grouped location rather than dated offer.
- MapLibre/OpenFreeMap or ADR-002 is replaced.
- The listing rail requires a ranking or availability claim not present in the
  current product requirements.
- Backend filtering/pagination ownership moves to the browser.
- The responsive target no longer requires the P-004 map-first mobile flow.
- A visual implementation requires a new production dependency or paid map
  service.

## Exit checklist

- [x] The question is answered within the stated scope.
- [x] Evidence and uncertainty are distinguishable.
- [x] Affected decisions and domain documents are linked.
- [x] Proposed task boundaries and dependencies are identified.
- [x] No production or disposable proof code was created.
- [x] `revision` represents the material content being submitted.
- [x] `status` is `awaiting_approval` and approval remains `pending`.

## Owner decision

The owner records the decision only in the YAML `approval` object. Approval of
spike revision 1 permits task refinement/promotion and implementation planning;
it does not permit code.
