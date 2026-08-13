---
schema: ai-workflow/implementation-plan@1
epic: E5
title: "Interactive M1 map and filters implementation plan"
status: approved
revision: 2
owner: owner
spike_revision: 2
task_sequence:
  - id: E5-T1
    revision: 2
  - id: E5-T2
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

# Implementation Plan: Interactive M1 map and filters

## Approved spike baseline

[E5 spike revision 2](SPIKE.md) approves the browser-visible grouped map/result interaction followed by URL-backed M1 filters/viewport lifecycle. Detail/media and later production UX work stay proposed.

## Scope and outcome

Render E4's generated contracts in a responsive, accessible MapLibre/OpenFreeMap experience. Users can select grouped pins/list entries, see dated offers, apply all M1 filters, share/reload state, and retain useful list/filter behavior when the map or API degrades.

## Ordered task sequence

### 1. E5-T1 — Build map shell and grouped pin interaction

- Task: [E5-T1 revision 2](tasks/E5-T1-build-map-shell-and-grouped-pin-interaction.md).
- Dependencies: E1-T2 is existing ancestry; E4-T2 must become the direct backend ancestor before start.
- Independent result: map/render/selection/accessibility review without filter-request complexity.
- Affected code: frontend dependencies, client-only map shell/layers, result list/panel, translations/styles/tests.
- Verification: generated-type compile, component/accessibility tests, seeded click flow, 360 px, production build.

### 2. E5-T2 — Add URL-backed filters and viewport querying

- Task: [E5-T2 revision 2](tasks/E5-T2-add-url-backed-filters-and-viewport-querying.md).
- Dependencies: E5-T1 direct ancestry and E4-T2 backend contract.
- Independent result: URL/filter/query lifecycle changes review separately from map rendering.
- Affected code: URL codec, controls, query provider/hooks, request cancellation/debounce, tests.
- Verification: codec/component/cancellation tests and reload/share/clear/move/filter end-to-end flow.

## Cross-task architecture

Server/API data uses generated OpenAPI types. Map components own rendering and transient selection only. URL parameters own public filter/viewport state. TanStack Query owns request lifecycle/cancellation/cache. The frontend never decides filter matching, facets, confidence, visibility, masking, permissions, or availability.

## Data and migrations

No database migration. Components consume E4 contracts and must tolerate additive fields. No source/media/contact data is introduced.

## Security and privacy

Only public generated responses reach the browser. Style URL is public configuration; no secret provider key. External tiles use the documented provider and attribution. Error UI does not print raw responses/internal URLs.

## Test and verification strategy

- Vitest/Testing Library for shell states, list/pin selection, panel, URL codec, controls, debounce/cancel, focus/labels.
- Contract/type checks against generated E4 schemas.
- Browser end-to-end seeded selection/filter/reload/clear/viewport flow.
- 360 px and desktop layout, keyboard operation, visible attribution/confidence, WebGL/tile/API degradation.
- ESLint/TypeScript/Prettier/Next production build/runtime image.

## Operations, rollout, and rollback

Configure a public OpenFreeMap style URL with a safe default. Roll out E5-T1 after E4-T2, then E5-T2. Either web release can roll back independently with no data change. Caddy/API health remains authoritative even when external tiles fail.

## Risks and mitigations

- **Browser-only import breaks build:** Client Component owns `next/dynamic({ssr:false})`; production build gate.
- **Canvas inaccessible:** semantic list/controls, focus tests, status messages.
- **Frontend business drift:** generated DTO rendering and backend facets only.
- **Request storm:** debounce, normalized keys, AbortSignal, bounded bbox.
- **Provider outage:** retain list/filter/result UI and visible degraded message.

## Invalidation triggers

Return to the spike for another renderer/provider, frontend-owned filtering/domain state, secret tile credentials, or expanded detail/media scope. Return to this plan for material component/task order/query/accessibility/rollout changes.

## Approval checklist

- [x] E5 spike revision 2 is explicitly approved/current.
- [x] E5-T1/T2 revision 2 are promoted with complete acceptance/traceability.
- [x] E4-T2/E5 ancestry is acyclic and start-gated.
- [x] Components, contracts, tests, accessibility, risks, rollout, and rollback are explicit.
- [x] No deferred decision blocks the synthetic M1 UI.
- [x] No implementation code was written before this plan approval.
- [x] Revision 2 records the approved plan.

## Owner decision

Flippylolz approved revision 2 through the delegated overnight MVP/autodeploy directive. Tasks still start in order on dedicated stacked branches; detail/media/Telegram/auth/contact behavior remains unauthorized.
