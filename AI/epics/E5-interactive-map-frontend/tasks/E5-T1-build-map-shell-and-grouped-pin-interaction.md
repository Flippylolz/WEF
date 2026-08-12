---
schema: ai-workflow/task@1
id: E5-T1
epic: E5
title: "Build map shell and grouped pin interaction"
status: draft
revision: 2
priority: P0
size: L
milestone: M1
dependencies: [E1-T2, E4-T2]
requirement_ids: [P-001, P-004, P-007]
decision_ids: [ADR-002, ADR-004, ADR-012]
deferred_decision_ids: []
promotion:
  source: ../proposed-tasks/E5-T1-build-map-shell-and-grouped-pin-interaction.md
  promoted_by: "Cursor Agent (owner-authorized)"
  promoted_at: "2026-08-12T22:34:40Z"
spike_gate:
  status: satisfied
  file: ../SPIKE.md
  approved_revision: 2
  verified_by: "Cursor Agent"
  verified_at: "2026-08-12T22:34:40Z"
implementation_gate:
  status: satisfied
  file: ../IMPLEMENTATION_PLAN.md
  approved_revision: 2
  verified_by: "Cursor Agent"
  verified_at: "2026-08-12T22:34:40Z"
dependency_gate:
  status: blocked
  verified_by: null
  verified_at: null
  evidence: []
branch:
  required: true
  name: null
  task_id: E5-T1
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

# E5-T1: Build map shell and grouped pin interaction

## Outcome

Render generated backend GeoJSON as an interactive Warsaw map with grouped pins, an accessible companion list, and a clickable dated-result panel.

## Scope

- Add current `maplibre-gl` and `react-map-gl` dependencies and load the map client-only from a stable shell.
- Use a configurable public OpenFreeMap style URL with visible OpenStreetMap/OpenFreeMap attribution.
- Render clustered GeoJSON `Source`/`Layer` data; cluster activation zooms to members and pin activation selects a location.
- Fetch the selected location's dated offer collection and render backend-provided labels/values in a desktop panel/mobile sheet.
- Provide a semantic companion list whose focus/activation coordinates with map selection.
- Preserve useful loading, empty, API-error, WebGL/tile-failure, and low-confidence states without inventing business meaning.

## Out of scope

- Filter controls/URL state/viewport debounce (E5-T2), full details, media/gallery, Telegram actions, auth/contacts, frontend domain logic, and a secret map provider key.

## Affected modules and contracts

- Next.js page/client map/result components, generated E4 types/client, translations/styles/tests, frontend dependencies.

## Implementation notes

- Import map components/types from `react-map-gl/maplibre` and MapLibre CSS once.
- `next/dynamic({ssr:false})` is declared from a Client Component.
- GeoJSON properties and offer summaries are rendered, not re-derived; no availability/status inference.
- Map canvas is supplemented by semantic controls/list; no pointer-only critical action.
- Selected IDs are transient UI state; public filters remain URL state in E5-T2.

## Acceptance criteria

- [ ] The seeded M1 dataset renders grouped pins centered on Warsaw and clicking a pin opens dated related offers.
- [ ] Clusters expand and pins/list items support pointer plus keyboard-operable selection where the library/browser permits.
- [ ] OpenStreetMap/OpenFreeMap attribution is always visible.
- [ ] Low-confidence/precision is represented with backend fields and not color alone.
- [ ] Loading, empty, API error, WebGL unsupported, and tile/style failure retain a useful accessible result/list state.
- [ ] Layout works at 360 px and desktop without horizontal page overflow.
- [ ] Generated API types are the only public data model and production build succeeds without browser globals during SSR/build.

## Test plan

- Unit/component: map shell states, feature/list selection, result panel, accessible names/focus, confidence/attribution.
- Contract: generated E4 response types.
- End-to-end: pointer/keyboard select seeded pin and read publication date through Caddy.
- Accessibility: semantic companion list, focus visibility/order, status announcements, 360 px.
- Production: Next build and runtime image.

## Rollout and rollback

Additive UI over E4 endpoints. A map/style failure degrades to list/results. Roll back the web image without database changes.

## Ready checklist

- [x] This file is authoritative under `tasks/`; the proposed source is removed.
- [x] Promotion, spike revision 2, and plan revision 2 are recorded.
- [ ] E4-T2 and E1-T2 are complete or recorded direct ancestors under ADR-018.
- [x] Scope and acceptance match the approved plan.

## Start checklist

- [ ] Status passes through `ready`.
- [ ] Dedicated E5-T1 branch is created and recorded.
- [ ] Branch/PR contain E5-T1 only.

## Done checklist

- [ ] Acceptance criteria pass.
- [ ] The global [definition of done](../../../workflow/DEFINITION_OF_DONE.md) passes.
- [ ] Completion actor, time, pull request, and evidence are recorded.
