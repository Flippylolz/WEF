---
schema: ai-workflow/spike@1
epic: E5
title: "Interactive map frontend research"
status: approved
revision: 2
owner: owner
research_only: true
code_allowed: false
decision_ids: [ADR-002, ADR-003, ADR-004, ADR-007, ADR-012]
domain_docs: [product, contracts, architecture, security]
proposed_task_ids: [E5-T1, E5-T2, E5-T3, E5-T4, E5-T5]
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

# Spike: Interactive map frontend

> Revision 2 is approved research. The spike remains non-executable; implementation requires its approved plan and promoted tasks.

## Question

How should the Next.js client render the backend contract as a responsive, accessible MapLibre map/list/detail experience without reimplementing filters, permissions, masking, or other domain behavior?

## Context and constraints

- MapLibre/OpenFreeMap is the accepted renderer/basemap and required attribution remains visible.
- Generated OpenAPI types and the typed client are the normal API source; URL parameters own public filter state.
- The client manages layout, interaction, focus, localization, request lifecycle, and transient state only.
- The interface must preserve filters through loading/errors and provide keyboard, mobile, WebGL-degraded, missing-media, and low-confidence states.

Governing domains:

- [Product](../../product/README.md)
- [Contracts](../../contracts/README.md)
- [Architecture](../../architecture/README.md)
- [Security](../../security/README.md)

Governing decisions and deferred gates:

- [ADR-002](../../decisions/adr/ADR-002-grouped-location-development-map.md)
- [ADR-003](../../decisions/adr/ADR-003-do-not-infer-current-availability.md)
- [ADR-004](../../decisions/adr/ADR-004-maplibre-openfreemap.md)
- [ADR-007](../../decisions/adr/ADR-007-mounted-media-storage-interface.md)
- [ADR-012](../../decisions/adr/ADR-012-backend-centric-modular-monolith.md)

## Research method

Map product interaction/quality criteria to component boundaries, generated API consumption, URL state, request cancellation, MapLibre lifecycle, responsive layout, accessibility/focus behavior, and media loading.

Research outputs must remain non-executable Markdown. Any data inspection must preserve source privacy and may not copy real source payload, contacts, credentials, sessions, or media into this artifact.

## Evidence

- P-001 through P-007 define grouped pins, details, filters, coordination, media, Telegram links, attribution, and confidence behavior.
- ADR-004 selects MapLibre/OpenFreeMap; ADR-012 forbids a second frontend domain/service layer.
- The roadmap requires 360 px behavior, WCAG 2.2 AA public flows, WebGL fallback, debounced viewport queries, and no full detail/media in initial map payloads.
- Current `react-map-gl` guidance uses `react-map-gl/maplibre`, `Source`/`Layer` for clustered GeoJSON, `interactiveLayerIds`, and `getClusterExpansionZoom`.
- Current Next.js App Router guidance loads browser-only libraries from a Client Component through `next/dynamic({ssr:false})`; URL state uses `useSearchParams`, `usePathname`, and `useRouter`.
- The existing web proof already consumes generated OpenAPI types and renders backend-owned labels without a frontend domain layer.

No private source/media is needed for this UI boundary.

## Options to evaluate

- Use feature-oriented map/offers components over generated query options, URL-backed filters, and local transient selection state.
- Introduce Redux/Zustand and client-side domain models initially, which adds duplicated state/rules without demonstrated need.
- Use a server-rendered static map, which cannot meet the accepted grouped-pin interaction.

## Approved recommendation

Promote E5-T1 and E5-T2 as separate stacked tasks. E5-T1 builds the client-only Warsaw map, clustered/pin interaction, selected-location summary panel, visible attribution, accessible companion list, and degraded states over generated E4 GeoJSON. E5-T2 adds URL-backed M1 filters and debounced viewport requests without recomputing backend semantics.

Keep detail/media and later accessibility/performance expansion in E5-T3 through E5-T5. The promoted tasks must still meet keyboard, 360 px, loading/error/empty/WebGL fallback, and production-build baselines appropriate to their included interactions.

## Proposed task boundaries

- [E5-T1: Build map shell and grouped pin interaction](tasks/E5-T1-build-map-shell-and-grouped-pin-interaction.md) — promote first.
- [E5-T2: Add URL-backed filters and viewport querying](tasks/E5-T2-add-url-backed-filters-and-viewport-querying.md) — promote as E5-T1 child.
- [E5-T3: Build offer detail and media gallery](proposed-tasks/E5-T3-build-offer-detail-and-media-gallery.md) — keep proposed.
- [E5-T4: Complete responsive list/map accessibility](proposed-tasks/E5-T4-complete-responsive-list-map-accessibility.md) — keep proposed.
- [E5-T5: Performance and production UX pass](proposed-tasks/E5-T5-performance-and-production-ux-pass.md) — keep proposed.

Only promoted E5-T1 and E5-T2 may appear in implementation-plan revision 2.

## Risks and open questions

- Map remounts and oversized payloads can harm the first useful render.
- Pointer-only interactions or unmanaged focus can fail accessibility.
- Frontend fallback logic can accidentally infer confidence, availability, or permissions.
- Canvas rendering is not itself accessible; keep a semantic companion result list and focusable selection controls.
- Tile/provider failure must not remove filters/results; preserve an API-backed degraded list state.
- Map style URL and attribution are public configuration; no secret map key is introduced.

## Invalidation triggers

- A change to this epic's outcome, accepted architecture/dependency direction, public or persisted contracts, security model, ingestion semantics, or deployment topology.
- A new external dependency or service that changes data handling, operations, licensing, secrets, or replacement paths.
- Evidence that a listed task boundary cannot remain independently reviewable or that a roadmap dependency is incomplete.

## Exit checklist

- [x] The bounded question is answered with evidence and uncertainty distinguished.
- [x] Governing domain documents and decisions are reviewed and linked.
- [x] Options, recommendation, risks, and open questions are complete.
- [x] E5-T1/T2 scope, acceptance, dependencies, priority/size, and traceability are refined.
- [x] No production or disposable proof code was created during the spike.
- [x] Revision 2 represents the approved material content.
- [x] Status and approval metadata record the delegated owner decision.

## Owner decision

Flippylolz approved revision 2 through the explicit overnight MVP/autodeploy delegation. This permits E5-T1/T2 promotion and planning only; code still requires approved plan revision 2 and task stack gates.
