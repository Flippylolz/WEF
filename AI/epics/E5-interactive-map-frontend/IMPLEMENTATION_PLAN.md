---
schema: ai-workflow/implementation-plan@1
epic: E5
title: "Complete interactive map frontend implementation plan"
status: approved
revision: 3
owner: owner
spike_revision: 3
task_sequence:
  - id: E5-T2
    revision: 2
  - id: E5-T3
    revision: 2
  - id: E5-T4
    revision: 2
  - id: E5-T5
    revision: 2
approval:
  required_role: owner
  status: approved
  decided_by: Flippylolz
  decided_at: "2026-08-13T19:30:00Z"
  approved_revision: 3
  evidence: "Owner approved the E5-only documentation-first stack for full E5 completion and assigned E3/E4 dependencies to parallel agents"
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# Implementation Plan: Complete interactive map frontend

## Approved spike baseline

[E5 spike revision 3](SPIKE.md) retains completed E5-T1 and approves the complete remaining frontend sequence: URL/filter/query lifecycle, generated-contract detail/media, responsive accessibility, and production performance/recovery. MapLibre/OpenFreeMap, backend-owned domain behavior, generated contracts, anonymous browsing, visible attribution, and no inferred availability remain binding.

## Scope and outcome

Deliver E5-T2 through E5-T5 as four ordered task PRs after this documentation PR. Users can share and reload canonical filters/viewport state, inspect dated offer details and media, complete the map/list/detail flow at 360 px and desktop widths with keyboard and screen-reader support, and recover usefully from API/tile/WebGL failures within a measured production performance budget.

E5 consumes E4 contracts only. E3/E4 task delivery is owned by parallel agents; this plan records those task IDs as hard start gates and never substitutes mocked or client-invented semantics.

## Ordered task sequence

### 1. E5-T2 — Add URL-backed filters and viewport querying

- Task: [E5-T2 revision 2](tasks/E5-T2-add-url-backed-filters-and-viewport-querying.md).
- Dependencies: completed E5-T1 and E4-T2.
- Independently reviewable result: canonical filter/viewport URL state and bounded backend requests without detail or layout expansion.
- Affected modules/contracts: URL codec, filter controls, query provider/hooks, catalog client, map viewport events, translations, styles, and tests over existing generated E4 query types.
- Verification: deterministic codec/default/repeated-value tests; every M1 filter; debounce, duplicate suppression, and `AbortSignal` propagation; reload/share/clear/move browser flow; keyboard, 360 px, and production build.
- Rollback: revert the web-only task; existing map/list behavior and backend contracts remain compatible.

### 2. E5-T3 — Build offer detail and media gallery

- Task: [E5-T3 revision 2](tasks/E5-T3-build-offer-detail-and-media-gallery.md).
- Dependencies: completed E5-T1 and E4-T3. E4-T3 must be done or represented by a valid ancestor PR before this task starts.
- Independently reviewable result: one generated-contract detail boundary with dated fields, masked text, confidence, history, media, and verified source action.
- Affected modules/contracts: catalog client, generated offer-detail types, detail drawer/sheet, media gallery, translations, styles, and focused component/contract tests.
- Verification: structured field and uncertainty rendering; no availability inference; matching/non-matching disclosure; lazy image/full-media behavior; native video controls; keyboard close/next/previous; safe external links; missing media/link/field states; no raw contacts, payloads, paths, or internal errors.
- Rollback: revert the frontend detail task without changing E4 or persisted media; the summary panel remains available.

### 3. E5-T4 — Complete responsive list/map accessibility

- Task: [E5-T4 revision 2](tasks/E5-T4-complete-responsive-list-map-accessibility.md).
- Dependencies: completed E5-T2 and E5-T3.
- Independently reviewable result: coordinated desktop split view and mobile map/bottom-sheet/full-list modes with complete focus and degraded-state behavior.
- Affected modules/contracts: explorer layout, map/list/detail coordination, focus management, semantic status/fallback UI, responsive styles, accessibility tests, and manual review evidence.
- Verification: 360 px and desktop flows; pointer, keyboard-only, and screen-reader/focus walkthroughs; visible focus; result/pin highlight coordination; loading/empty/API/tile/WebGL states; automated accessibility checks against the agreed WCAG 2.2 AA target.
- Rollback: revert layout/focus changes to E5-T3 behavior; no API or data rollback.

### 4. E5-T5 — Performance and production UX pass

- Task: [E5-T5 revision 2](tasks/E5-T5-performance-and-production-ux-pass.md).
- Dependencies: completed E5-T4 and E4-T4. E4-T4 must be done or represented by a valid ancestor PR before this task starts.
- Independently reviewable result: measured frontend budgets, stable map lifecycle, deferred detail/media loading, metadata/error boundaries, and actionable recovery UX.
- Affected modules/contracts: Next configuration, route metadata/error boundaries, map lifecycle, image/detail loading, web-vitals instrumentation, outage recovery UI, and performance regression tests.
- Verification: recorded device/viewport/network/data profile and target; initial payload excludes full detail/media; map instance survives filter/selection changes; lazy media sizing prevents layout breakage; API/tile failures preserve state and offer retry/list actions; production build and runtime image pass.
- Rollback: revert optimization/recovery changes as one web release; no schema, data, or media deletion.

## Cross-task architecture

Server/API data uses generated OpenAPI types. URL parameters own canonical public filter/viewport state; TanStack Query owns request lifecycle, cancellation, and cache; components own rendering, layout, focus, and transient selection/gallery state. Query keys use normalized URL values, and each query function passes the supplied `AbortSignal` to the generated client transport.

The initial map and location-offer collection remain compact. E5-T3 fetches full detail/media only after explicit offer selection. E5-T4 composes existing map, list, and detail boundaries instead of creating a second store. E5-T5 measures and optimizes those boundaries without moving filter matching, facets, confidence, visibility, masking, verified-link capability, permissions, or availability decisions into the frontend.

Stack order is documentation → E5-T2 → E5-T3 → E5-T4 → E5-T5. Each task branches from and targets its immediate E5 predecessor. Before E5-T3/E5-T5 branch creation, the stack must include the exact E4 dependency through completed `main` ancestry or a documented valid ancestor PR; parallel E3/E4 work is not copied into an E5 task.

## Data and migrations

E5 has no database or media migration and performs no source/media writes. Components consume committed E4 contracts and tolerate documented additive fields. Browser state contains public URL filters, public API DTOs, and transient selected IDs only. Rollback cannot remove or alter E3/E4 data and requires no data recovery.

## Security and privacy

Only public generated responses reach the browser. The UI renders only server-masked source text, server-provided confidence/capabilities, opaque public media URLs, and a verified Telegram URL when present. It never constructs a link from unverified channel/message input, exposes contacts/raw payloads/internal paths/provider responses, or prints raw error bodies/internal URLs.

External source links open with safe new-tab attributes. Style URL is public configuration; no secret provider key is introduced. Required OpenStreetMap/OpenFreeMap attribution remains visible. Detail/media requests remain anonymous public reads; registration and contact reveal remain outside E5.

## Test and verification strategy

- Unit tests cover canonical URL parse/serialize/default omission, normalized query keys, debounce/abort behavior, formatting, and recovery-state reducers/helpers where introduced.
- Testing Library covers facet controls, selection/detail/gallery behavior, uncertainty and missing-data states, focus restoration, keyboard operation, accessible names/statuses, and map-independent fallback behavior.
- Contract tests and generated-type compilation prove E4 query/detail/media DTO consumption without handwritten response models. API errors use stable backend machine codes when available and safe generic presentation otherwise.
- Browser flow covers filter/share/reload/clear/viewport, pin/list/offer selection, detail close, gallery operation, verified/missing source actions, mobile list mode, and API/tile/WebGL degradation.
- Accessibility evidence combines automated checks with a recorded keyboard and screen-reader/focus walkthrough at 360 px and desktop widths.
- Performance evidence records the agreed profile, route/build output, initial payload boundary, map-instance stability, and web-vitals observations without sending private listing/source data.
- Every task runs the repository's frozen install, formatting, lint, type, unit/contract checks, production build, repository safety, and runtime image CI. A child PR is not opened until its parent PR is freshly green.

## Operations, rollout, and rollback

Roll out only after dependencies are merged base-first: documentation, E5-T2, E4-T3 then E5-T3, E5-T4, E4-T4 then E5-T5. When a parallel E4 dependency lands after this stack starts, refresh the direct E5 ancestor from current `main`, rerun required CI, and record the exact dependency evidence before creating the dependent E5 branch.

The public OpenFreeMap style URL retains its safe default and visible attribution. Caddy/API health remains authoritative even when external tiles fail. Each E5 task is web-only and can roll back by reverting its squash commit or prior web image; no database downgrade, media deletion, or source replay is required. A rollback to an older web image requires the additive E4 API version to remain compatible.

## Risks and mitigations

- **Browser-only import breaks build:** Client Component owns `next/dynamic({ssr:false})`; production build gate.
- **Search-param prerender failure:** isolate App Router search hooks in a Client Component under `Suspense`; production build gate.
- **Canvas inaccessible or focus lost:** semantic list/controls, explicit dialog/sheet labels, focus entry/restoration, automated and manual evidence.
- **Frontend business drift:** generated DTO rendering, backend facets/capabilities only, and negative tests for availability/link inference.
- **Request storm or stale result race:** bounded bbox, debounce, deterministic keys, duplicate suppression, and consumed `AbortSignal`.
- **Oversized eager payload:** keep map/collection summaries compact; fetch detail/media only after selection and lazy-load full assets.
- **Map remount regression:** stable component/key boundaries plus map-instance lifecycle regression coverage.
- **Provider/API outage:** retain controls, URL, list/previous safe state, visible degraded status, and actionable retry/list paths.
- **Parallel contract drift:** block E5-T3/E5-T5 until exact E4 revisions are present; material response/behavior changes return to the spike/plan instead of adding adapters by guesswork.

## Invalidation triggers

Return to the spike for another renderer/provider, frontend-owned domain/filter/masking/capability behavior, secret tile credentials, authentication/contact reveal, non-public media handling, a material E4 public-contract change, or a changed epic outcome. Return to this plan for material task order/dependency, component/state boundary, URL schema, accessibility target/evidence, performance profile/budget, test, rollout, or rollback changes.

## Approval checklist

- [x] E5 spike revision 3 is explicitly approved and current.
- [x] E5-T2 through E5-T5 are promoted with complete acceptance criteria and traceability.
- [x] The E5-T2 → E5-T3 → E5-T4 → E5-T5 delivery order and E4-T3/E4-T4 start gates are acyclic and enforceable.
- [x] Components, contracts, tests, accessibility, security, performance, risks, rollout, and rollback are explicit.
- [x] No E5 task has an unresolved deferred decision; incomplete E4 task dependencies remain explicit task gates.
- [x] No E5-T2 through E5-T5 implementation code was written before this plan approval.
- [x] Revision 3 and its separate owner approval are recorded.

## Owner decision

Flippylolz approved revision 3 by selecting the E5-only documentation-first stack for full epic completion and assigning E3/E4 dependencies to parallel agents. This authorizes only E5-T2 through E5-T5 under the sequence, boundaries, dependency gates, tests, and green-parent-CI rule above.
