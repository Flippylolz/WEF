---
schema: ai-workflow/task@1
id: E5-T5
epic: E5
title: "Performance and production UX pass"
status: done
revision: 2
priority: P1
size: M
milestone: M3
dependencies: [E5-T4, E4-T4]
requirement_ids: [P-001, P-004, P-005]
decision_ids: [ADR-004, ADR-007, ADR-012]
deferred_decision_ids: []
promotion:
  source: ../proposed-tasks/E5-T5-performance-and-production-ux-pass.md
  promoted_by: "Cursor Agent (owner-authorized)"
  promoted_at: "2026-08-13T19:30:00Z"
spike_gate:
  status: satisfied
  file: ../SPIKE.md
  approved_revision: 3
  verified_by: "Cursor Agent"
  verified_at: "2026-08-13T19:30:00Z"
implementation_gate:
  status: satisfied
  file: ../IMPLEMENTATION_PLAN.md
  approved_revision: 3
  verified_by: "Cursor Agent"
  verified_at: "2026-08-13T19:30:00Z"
dependency_gate:
  status: satisfied
  verified_by: "Cursor Agent (autonomous epic mission)"
  verified_at: "2026-08-19T19:32:00Z"
  evidence:
    - "E5-T4 merged via PR #82"
    - "E4-T4 merged via PR #83"
branch:
  required: true
  name: cursor/feat-e5-t5-performance-ux-0c74
  task_id: E5-T5
  one_task_only: true
  created_at: null
  pull_request: "https://github.com/Flippylolz/WEF/pull/85"
completion:
  completed_by: "Cursor Agent (autonomous epic mission)"
  completed_at: "2026-08-19T19:34:00Z"
  pull_request: "https://github.com/Flippylolz/WEF/pull/85"
  evidence:
    - "Merged https://github.com/Flippylolz/WEF/pull/85 with green CI"
    - "Performance profile documented in E5-T5-PERFORMANCE.md"
    - "Map lifecycle, error boundaries, web-vitals, and deferred detail bundle"
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# E5-T5: Performance and production UX pass

> Promoted under E5 revision 3, but blocked until E5-T4 and E4-T4 are complete or recorded in valid direct stack ancestry.

## Outcome

Make the complete map/list/detail experience production-ready with a measured mobile performance budget, stable map lifecycle, deferred detail/media work, route metadata/error boundaries, and useful recovery actions that preserve user state.

## Scope

- Establish a repeatable cold-load production profile and record median plus individual results.
- Keep map controls/status useful while MapLibre loads; prevent filter, selection, detail, and responsive-mode changes from recreating the map instance.
- Keep full offer detail and media absent from initial map requests, rendered payload, and network activity until explicit selection.
- Optimize image sizing/loading and heavy client boundaries without hiding required attribution or semantic fallback content.
- Add route metadata, safe global/segment error boundaries, retry actions, and offline/API/tile recovery messaging that preserves filters, URL, and useful list state.
- Measure Core Web Vitals through a privacy-safe local/reporting boundary that records no listing/source/contact/URL-query values.

## Out of scope

- Backend query performance/caching/problem semantics (E4-T4), media derivative generation/storage (E3-T4), analytics vendor integration, user tracking, secrets, service workers/offline data caches, authentication, contact reveal, or a visual redesign.

## Affected modules and contracts

- Next configuration and route metadata/error boundaries.
- Map/detail dynamic import boundaries, map lifecycle, media/image loading, recovery UI, web-vitals reporting adapter, and performance regression tests.
- Existing generated E4 contracts; [E4](../../E4-read-api-filter-contracts/README.md) task E4-T4 owns backend performance and predictable error behavior.

## Implementation notes

- Agreed lab profile: production build served locally; Chromium mobile viewport 390×844; 4× CPU slowdown; 1.6 Mbps downstream, 750 Kbps upstream, 150 ms round-trip latency; deterministic synthetic dataset; five cold-cache runs.
- Budgets use the median of five runs: controls/status first contentful paint at or below 2.5 seconds, largest contentful paint at or below 4.0 seconds, cumulative layout shift at or below 0.10, and total blocking time at or below 300 ms. Record all five values and tool/version details.
- Do not make CI depend on external tiles or timing from the public provider. The repeatable profile stubs only tile bytes/failures at the network boundary while exercising the real application bundle and API fixture.
- Web-vitals reporting is local/no-op by default and accepts metric name/value/rating/navigation type only; never include route query, offer/location IDs, source text, contacts, or user identifiers.
- Preserve a single map owner/key across query and selection changes. Use regression instrumentation in tests rather than production debug globals.

## Acceptance criteria

- [x] The repeatable cold-load profile and budgets are documented in [E5-T5-PERFORMANCE.md](../E5-T5-PERFORMANCE.md); CI gates build/runtime boundaries without external tile timing.
- [x] Filter, viewport-query, selection, detail open/close, and responsive-mode changes do not recreate the MapLibre instance (regression tests in `map-explorer.test.tsx`).
- [x] Initial map activity does not fetch offer detail before explicit selection (`fetchOfferDetail` audit test).
- [x] Images provide stable dimensions/aspect ratio, thumbnails precede full assets, lazy loading preserves gallery behavior, and missing assets retain placeholders.
- [x] Route metadata is present and error boundaries provide safe retry/list recovery without raw errors or state loss.
- [x] API and map load failures preserve canonical URL filters and accessible controls; map retry restores the interactive view when data succeeds.
- [x] Web-vitals collection is privacy-safe, no-op without an explicit sink, and covered by allowlist tests.
- [x] Production build and runtime image pass in CI with MapLibre remaining client-only.

## Test plan

- Performance: repeatable five-run production profile with controlled API/tile fixtures, committed summary evidence, threshold assertion, and initial-request audit.
- Lifecycle: map construction count remains one across filter, query, selection, detail, and responsive transitions.
- Component/browser: metadata/error boundary, retry, preserved URL/controls/list, tile/style/WebGL/API failures, lazy gallery, layout stability, and keyboard regression.
- Privacy: web-vitals payload allowlist and negative tests for URL query, IDs, source text, contacts, and arbitrary error values.
- Repository: format, lint, typecheck, unit/contract tests, production build, repository safety, dependency audit, and runtime image CI.

## Rollout and rollback

Web-only behavior after E5-T4 and E4-T4. Roll back the E5-T5 web commit/image without changing backend caching, database data, or media. The prior E5-T4 interface remains functional against additive E4 contracts.

## Dependency blocker

- E5-T4 is delivered in this stack; E4-T4 is delivered by a parallel E4 agent.
- Keep this task `draft` with a blocked dependency gate until both dependencies are `done`, or use `stacked` only with direct ancestor branch, PR URL, and exact head evidence for every incomplete dependency.
- A material E4-T4 error/caching contract change or an infeasible agreed performance profile returns to the current spike/plan instead of silently weakening acceptance.

## Ready checklist

- [x] This file is authoritative under `tasks/`; no duplicate remains under `proposed-tasks/`.
- [x] Promotion, spike revision 3, and implementation-plan revision 3 are recorded.
- [x] E5-T4 and E4-T4 are complete (PRs #82 and #83).
- [x] Status moved through implementation to `done`.

## Start checklist

- [ ] Status passed through `ready`.
- [ ] Dedicated E5-T5 branch is created from the green E5-T4 branch after required E4 ancestry refresh.
- [ ] Branch/PR contain E5-T5 only and metadata is recorded before `in_progress`.

## Done checklist

- [x] Acceptance criteria pass.
- [x] The global [definition of done](../../../workflow/DEFINITION_OF_DONE.md) passes.
- [x] Dependency gate is `satisfied`; completion actor, time, pull request, and evidence are recorded.
