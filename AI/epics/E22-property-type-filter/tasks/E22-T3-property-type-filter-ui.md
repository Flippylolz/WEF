---
schema: ai-workflow/task@1
id: E22-T3
epic: E22
title: "Add the URL-backed property type filter UI"
status: draft
revision: 1
priority: P1
size: M
milestone: M5
dependencies: [E13-T3, E22-T2]
requirement_ids: [P-002, P-003, P-004, P-010]
decision_ids: [ADR-002, ADR-004, ADR-012, ADR-013]
deferred_decision_ids: []
promotion:
  source: ../proposed-tasks/E22-T3-property-type-filter-ui.md
  promoted_by: "Codex agent (owner-approved E22 spike revision 1)"
  promoted_at: "2026-09-02T15:46:31Z"
spike_gate:
  status: satisfied
  file: ../SPIKE.md
  approved_revision: 1
  verified_by: "Codex agent"
  verified_at: "2026-09-02T15:46:31Z"
implementation_gate:
  status: satisfied
  file: ../IMPLEMENTATION_PLAN.md
  approved_revision: 2
  verified_by: "Codex agent"
  verified_at: "2026-09-02T15:58:32Z"
dependency_gate:
  status: blocked
  verified_by: null
  verified_at: null
  evidence: []
branch:
  required: true
  name: null
  task_id: E22-T3
  one_task_only: true
  created_at: null
  pull_request: null
completion:
  completed_by: null
  completed_at: null
  pull_request: null
  evidence: []
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# E22-T3: Add the URL-backed property type filter UI

## Outcome

Visitors can select Apartment, House, and Semi-detached house in the map explorer,
see the active selection, and share or revisit the same filtered view.

## Scope

- Add generated-type-backed property selections to map search state, URL parsing,
  canonical serialization, and catalog API request mapping.
- Render facets-driven accessible checkboxes for Apartment, House, and
  Semi-detached house (`bliźniak`) in stable product order.
- Add property type to the active filter count/chip, group removal, Clear filters,
  and draft/apply behavior.
- Render the property type on listing cards and offer detail, with a neutral
  “Not classified” label for `unknown`.
- Preserve URL selections when facets are loading or unavailable and handle a
  valid deep-linked value absent from current facets without silently deleting it.
- Add component, URL-state, accessibility, responsive, and critical browser tests.

## Out of scope

- Backend classification/query behavior, taxonomy expansion, or new localization
  catalogs.
- A selectable Unknown option or a single-select-only radio control.
- UI guesses based on other displayed offer fields.

## Affected modules and contracts

- Map search state, URL parser/serializer, and catalog API parameter mapping.
- Filter controls, filter chips/count/reset, map explorer orchestration, listing
  cards, offer detail, and English message catalog.
- Generated API types from E22-T2; no hand-written duplicate enum.
- Component, URL-state, accessibility, mocked browser, and production-build tests.

## Implementation notes

- Empty selection is the default and sends no `property_type` parameter.
- Preserve valid URL selections while facets load or fail; merge deep-linked
  values into renderable options without inventing labels.
- Use the existing checkbox-group, draft/apply, active-chip, and responsive panel
  patterns. Keep Property type visibly distinct from Offer type.
- All result labels come from the API enum plus localized messages; no local
  inference from content/market type or text.

## Work

- Treat an empty selection as the default/unfiltered state.
- Allow multiple selections because the existing backend categorical convention is
  OR within a group and buyers may want both house categories.
- Keep URL ordering deterministic and deduplicate values.
- Reuse existing filter-panel, checkbox-group, chip, and responsive sheet patterns.

## Acceptance criteria

- [ ] Each type and every multi-selection sends the correct repeated
  `property_type` parameter to map, viewport, and location-offer requests.
- [ ] Reload, shared URLs, and browser back/forward restore the same selection.
- [ ] The active filter chip/count and per-group removal are accurate; Clear
  filters removes the property constraint without changing default content types.
- [ ] A facets error does not erase valid URL state or prevent applying/removing it.
- [ ] Cards/details show Apartment, House, Semi-detached house, or Not classified
  from the API value and never infer it locally.
- [ ] Controls are keyboard-operable, have a useful group legend and labels, and
  pass existing accessibility checks on desktop and mobile.
- [ ] Empty/loading/error behavior preserves selections and communicates the same
  way as existing filter groups.
- [ ] Component, URL-state, mocked browser, typecheck, contract, and production
  build checks pass.

## Dependencies and gates

- E13-T3 is done and supplies the current selectable map/list explorer.
- E22-T2 must be done or represented by a valid direct ancestor stack before work;
  it must be done before E22-T3 completes.
- Requires the E22 approval, promotion, dependency, and dedicated-branch gates.

## Risks and notes

The UI must not confuse physical property type with the existing Offer type
(Development posts vs Individual units). Use the legend **Property type** and keep
the two groups visually and semantically distinct.

## Test plan

- Unit: URL parse/serialize/dedup/order, API mapping, single/multi select,
  chip/count/group removal, clear, and unknown display label.
- Integration: explorer requests and state transitions across filter apply,
  viewport refresh, selected location, facets loading/error, and empty results.
- Contract/migration: generated TypeScript compiles against committed E22-T2
  OpenAPI; no migration in this task.
- End-to-end: desktop/mobile selection, combined choice, reload/share/back/forward,
  clear, and result/detail labels over sanitized route mocks.
- Security/accessibility/operations: keyboard/screen-reader labels, no source-text
  inference, production build and post-deploy smoke.

## Rollout and rollback

Deploy after E22-T2 is live and classified facets exist. Smoke all three choices,
a combined deep link, clear, desktop, and mobile. Rollback uses the prior web image;
the additive backend contract and classified data remain harmless.

## Ready checklist

- [x] The file is authoritative under `tasks/`; no duplicate remains under
  `proposed-tasks/`.
- [x] Promotion source, promoter, and timestamp are recorded.
- [x] `spike_gate` references approved E22 spike revision 1.
- [x] `implementation_gate` references an approved plan containing this task and
  revision.
- [ ] E13-T3 and E22-T2 have satisfied dependency evidence before `ready`.
- [x] Scope and acceptance criteria match approved spike revision 1.
