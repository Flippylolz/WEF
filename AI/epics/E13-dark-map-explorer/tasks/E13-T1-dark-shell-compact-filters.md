---
schema: ai-workflow/task@1
id: E13-T1
epic: E13
title: "Build the dark application shell and compact filter experience"
status: done
revision: 1
priority: P1
size: L
milestone: M4
dependencies: []
requirement_ids: [P-004]
decision_ids: [ADR-002, ADR-003, ADR-004, ADR-012, ADR-013]
deferred_decision_ids: []
promotion:
  source: ../SPIKE.md#proposed-task-boundaries
  promoted_by: "ZCode agent (owner-directed E13 implementation mission)"
  promoted_at: "2026-08-26T18:45:03Z"
spike_gate:
  status: satisfied
  file: ../SPIKE.md
  approved_revision: 1
  verified_by: "ZCode agent (owner-directed E13 implementation mission)"
  verified_at: "2026-08-26T18:45:03Z"
implementation_gate:
  status: satisfied
  file: ../IMPLEMENTATION_PLAN.md
  approved_revision: 1
  verified_by: "ZCode agent (owner-directed E13 implementation mission)"
  verified_at: "2026-08-26T18:45:03Z"
dependency_gate:
  status: satisfied
  verified_by: "ZCode agent (owner-directed E13 implementation mission)"
  verified_at: "2026-08-26T18:45:03Z"
  evidence: []
branch:
  required: true
  name: feat/E13-T1-dark-shell-compact-filters
  task_id: E13-T1
  one_task_only: true
  created_at: "2026-08-26T18:45:03Z"
  pull_request: null
completion:
  completed_by: "ZCode agent (owner-directed E13 implementation mission)"
  completed_at: "2026-08-27T01:34:36Z"
  pull_request: null
  evidence:
    - "Dark shell/rail/chips/drawer implemented; 130 vitest tests green at 94.93%/90.86% coverage; lint/typecheck/build green"
    - "Local stack visual verification at 1440x900 and 360x800 (dark map, one attribution, chips, drawer dialog)"
    - "OpenFreeMap dark style verified 2026-08-26; Dockerfile/compose/deploy smoke/rollback default switched to styles/dark"
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# E13-T1: Build the dark application shell and compact filter experience

## Outcome

The explorer becomes a dark, full-height, map-first application: a compact
application bar, a persistent left discovery rail whose results are visible
immediately below compact filter controls, a dark map filling the remaining
space with exactly one attribution surface, and a responsive mobile
map-first flow — using only existing contracts.

## Scope

- Dark design tokens from `UX_DESIGN.md` (background/surface/foreground/
  muted/border/accent/focus/warning/error), dark system color-scheme, WCAG
  2.2 AA contrast in all text/surface combinations.
- Application bar 56–64 px with the WEF wordmark, filter entry, favorites
  (Saved), and account controls; the floating account toolbar joins the bar.
- Left discovery rail `clamp(22rem, 30vw, 26rem)` with its own scroll region;
  map fills the remaining width and full application height; rail/map
  separated by a 1 px border.
- Compact filter experience: applied-filter chips with values and accessible
  remove actions plus backend quick filters in one wrapping row; the full
  filter form opens in an accessible drawer (native dialog) with the existing
  draft/Apply/Clear URL lifecycle; the form no longer permanently displaces
  results.
- Sticky results header (count + map-area scope) followed immediately by the
  grouped-location cards, relabeled as places with name, address,
  confidence, and matching-offer count.
- Dark map: verified OpenFreeMap `styles/dark` (planning evidence
  2026-08-26), restyled district fills/boundaries, clusters, default and
  low-confidence pins, hover/selected halos, focus-visible ring token;
  remove the duplicate custom attribution overlay and keep exactly one
  complete MapLibre attribution control.
- Mobile: compact top bar, bottom result-count control, existing
  sheet/full-list modes restyled dark; filter drawer becomes a full-height
  modal sheet with sticky Apply/Clear.
- Preserve URL-backed filters, map instance lifecycle, selection semantics,
  favorites, auth, loading/error/empty states, keyboard operation, live
  announcements, and reduced-motion behavior.

## Out of scope

- Offer-card rail and the new listings contract (E13-T2/T3).
- Functional text search input (no contract exists; none is faked).
- Media thumbnails, availability language, facet normalization.

## Affected modules and contracts

- `apps/web/src/app/page.tsx`, `layout.tsx`, `globals.css`.
- `apps/web/src/components/map-explorer.tsx`, `map-filter-controls.tsx`,
  `quick-filter-bar.tsx`, `warsaw-map.tsx`, `user-toolbar.tsx`.
- `apps/web/messages/en.json`; `scripts/deploy/smoke.sh` map-style check.
- No API contract change; generated client unchanged.

## Acceptance criteria

- [x] Desktop (≥56.0625rem) renders one full-height shell: app bar, left
      rail, full-bleed dark map; results appear without scrolling past the
      filter form.
- [x] Dark tokens applied application-wide; no light-theme remnants in the
      explorer, drawers, dialogs, or map overlays; theme color updated.
- [x] Filter chips show concise applied values with accessible remove
      actions; quick filters render in the same row; the full form opens in
      a labeled drawer that traps focus, supports Escape/close, and reuses
      the existing Apply/Clear URL flow.
- [x] Exactly one attribution surface remains on the map.
- [x] Mobile keeps map-first sheet/full-list modes with a dark full-height
      filter sheet; 360 px width has no horizontal scrolling.
- [x] URL filter share/reload, favorites, auth modal, offer detail drawer,
      keyboard paths, live announcements, and reduced-motion all keep
      working; existing unit/a11y/e2e suites updated and green.
- [x] `scripts/deploy/smoke.sh` verifies the dark style URL deployment-wide.

## Test plan

- Unit: chips/drawer lifecycle, applied-value summary strings, rail state
  rendering, map style/fallback constants.
- Integration/a11y: keyboard focus order in drawer and rail, announcements,
  contrast-token smoke, mobile sheet behavior.
- E2e: existing Playwright suite green under `NEXT_PUBLIC_WEF_DISABLE_MAP=1`.
- Manual/visual: 1440×900, 1024×768, 360×800 against the UX design matrix.

## Rollout and rollback

- Frontend-only release via the standard main-merge deploy; rollback is the
  prior web image.

## Ready checklist

- [x] Authoritative under `tasks/`; promoted from the approved spike.
- [x] Spike and implementation gates reference approved revision 1.
- [x] No dependencies; dependency gate satisfied with empty evidence.
- [x] Scope matches implementation plan revision 1.
