---
schema: ai-workflow/spike@1
epic: E5
title: "Interactive map frontend research"
status: approved
revision: 3
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
  decided_at: "2026-08-13T19:30:00Z"
  approved_revision: 3
  evidence: "Owner explicitly directed completion of full E5 as a documentation PR followed by one green-CI task PR per stacked branch; E3 and E4 dependencies are handled by parallel agents"
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# Spike: Interactive map frontend

> Revision 3 is approved research for the complete E5 sequence. The spike remains non-executable; implementation requires its approved plan, promoted tasks, and task-specific dependency gates.

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
- Current `react-map-gl` guidance uses the MapLibre-specific import, controlled `viewState`/`onMove`, map refs for bounded imperative reads, and `Source`/`Layer` plus `interactiveLayerIds` for clustered GeoJSON.
- Current Next.js App Router guidance limits `useSearchParams`, `usePathname`, and `useRouter` to Client Components and requires a `Suspense` boundary around prerendered routes that use search parameters.
- Current TanStack Query guidance deterministically hashes object members in query keys and cancels/reverts an obsolete query when its supplied `AbortSignal` is consumed by `fetch`.
- The public HTTP contract keeps map payloads compact and defines a separate offer-detail response with server-masked text, confidence, ordered public media metadata, verified source action, and history.
- The existing web proof already consumes generated OpenAPI types, renders backend-owned labels without a frontend domain layer, and retains an accessible companion list when the map degrades.
- E5-T1 is complete. E5-T2 can start against the completed E4-T2 contract; E5-T3 and E5-T5 must wait for E4-T3 and E4-T4 respectively, which are being delivered outside this epic.

No private source/media is needed for this UI boundary.

## Options considered

- **Selected:** deliver URL/query lifecycle, offer detail/media, responsive accessibility, and production performance as four ordered task PRs over generated contracts. This keeps each behavior independently reviewable and preserves backend authority.
- **Rejected:** combine the remaining work into one frontend PR. It would couple contract integration, interaction, accessibility, and performance evidence into an unsafe review and rollback unit.
- **Rejected:** build mocked detail/media contracts while E4-T3 is incomplete. That would invent public semantics and create a second client-owned contract.
- **Rejected:** introduce Redux/Zustand and client-side domain models. URL state, TanStack Query server state, and local transient interaction state cover the accepted needs without duplicated domain rules.
- **Rejected:** use a server-rendered static map. It cannot meet grouped-pin, viewport, list coordination, and degraded interactive behavior.

## Approved recommendation

Retain completed E5-T1 and deliver E5-T2 through E5-T5 as one ordered, documentation-first stack:

1. E5-T2 adds canonical URL-backed M1 filters and bounded viewport querying.
2. E5-T3 consumes E4-T3's generated offer-detail contract for a dated detail drawer and accessible media gallery.
3. E5-T4 completes desktop/mobile map-list-detail coordination and WCAG 2.2 AA evidence.
4. E5-T5 establishes the agreed performance profile, prevents map reinitialization, and adds production-grade recovery UX.

The frontend renders backend-owned filtering, masking, confidence, visibility, history, media URLs, and verified source capabilities. It may own URL syntax/default omission, request lifecycle, component layout, focus, and transient selection only.

## Proposed task boundaries

- [E5-T1: Build map shell and grouped pin interaction](tasks/E5-T1-build-map-shell-and-grouped-pin-interaction.md) — completed foundation.
- [E5-T2: Add URL-backed filters and viewport querying](tasks/E5-T2-add-url-backed-filters-and-viewport-querying.md) — first remaining task.
- [E5-T3: Build offer detail and media gallery](tasks/E5-T3-build-offer-detail-and-media-gallery.md) — starts only when E4-T3 is in direct ancestry or done.
- [E5-T4: Complete responsive list/map accessibility](tasks/E5-T4-complete-responsive-list-map-accessibility.md) — follows E5-T2 and E5-T3.
- [E5-T5: Performance and production UX pass](tasks/E5-T5-performance-and-production-ux-pass.md) — follows E5-T4 and starts only when E4-T4 is in direct ancestry or done.

## Risks and open questions

- Map remounts and oversized payloads can harm the first useful render.
- Pointer-only interactions or unmanaged focus can fail accessibility.
- Frontend fallback logic can accidentally infer confidence, availability, or permissions.
- Canvas rendering is not itself accessible; keep a semantic companion result list and focusable selection controls.
- Tile/provider failure must not remove filters/results; preserve an API-backed degraded list state.
- Map style URL and attribution are public configuration; no secret map key is introduced.
- Parallel E3/E4 delivery can change generated detail/media fields. E5-T3 and E5-T5 remain dependency-blocked until the exact E4 revisions are available; material contract changes return to this spike.
- The performance target needs a reproducible profile. E5-T5 must record device/viewport/network/data conditions with the measured budget instead of claiming an environment-free score.

## Invalidation triggers

- A change to this epic's outcome, accepted architecture/dependency direction, public or persisted contracts, security model, ingestion semantics, or deployment topology.
- A new external dependency or service that changes data handling, operations, licensing, secrets, or replacement paths.
- Evidence that a listed task boundary cannot remain independently reviewable or that a roadmap dependency is incomplete.

## Exit checklist

- [x] The bounded question is answered with evidence and uncertainty distinguished.
- [x] Governing domain documents and decisions are reviewed and linked.
- [x] Options, recommendation, risks, and open questions are complete.
- [x] E5-T1 through E5-T5 scope, acceptance, dependencies, priority/size, and traceability are refined.
- [x] No production or disposable proof code was created during the spike.
- [x] Revision 3 represents the approved material content.
- [x] Status and approval metadata record the delegated owner decision.

## Owner decision

Flippylolz approved revision 3 by explicitly directing full E5 completion, accepting the documentation-first five-PR stack, and assigning E3/E4 dependencies to parallel agents. This permits promotion and planning for all E5 tasks; code still requires approved plan revision 3 and each task's dependency/branch gates.
