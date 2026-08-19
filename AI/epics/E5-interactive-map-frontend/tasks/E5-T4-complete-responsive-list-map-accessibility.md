---
schema: ai-workflow/task@1
id: E5-T4
epic: E5
title: "Complete responsive list/map accessibility"
status: done
revision: 2
priority: P1
size: L
milestone: M3
dependencies: [E5-T2, E5-T3]
requirement_ids: [P-001, P-002, P-003, P-004, P-005]
decision_ids: [ADR-002, ADR-004, ADR-012]
deferred_decision_ids: []
promotion:
  source: ../proposed-tasks/E5-T4-complete-responsive-list-map-accessibility.md
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
  verified_at: "2026-08-19T18:56:00Z"
  evidence:
    - "E5-T2 | done | merged PR #43"
    - "E5-T3 | done | merged PR #80"
branch:
  required: true
  name: cursor/feat-e5-t4-responsive-a11y-0c74
  task_id: E5-T4
  one_task_only: true
  created_at: "2026-08-19T18:56:00Z"
  pull_request: null
completion:
  completed_by: "Cursor Agent (autonomous epic mission)"
  completed_at: "2026-08-19T19:08:00Z"
  pull_request: "https://github.com/Flippylolz/WEF/pull/82"
  evidence:
    - "Merged https://github.com/Flippylolz/WEF/pull/82 with green CI"
    - "Accessibility walkthrough recorded in E5-T4-A11Y-WALKTHROUGH.md"
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# E5-T4: Complete responsive list/map accessibility

> E5-T2 and E5-T3 are done (PR #43 and PR #80). Implementation is in progress on `cursor/feat-e5-t4-responsive-a11y-0c74`.

## Outcome

Complete the coordinated map/list/detail experience as a desktop split view and mobile map/bottom-sheet/full-list flow with deterministic focus, keyboard and screen-reader operation, and useful non-map states meeting the agreed WCAG 2.2 AA target.

## Scope

- Refine desktop map/results/detail proportions and mobile map-first bottom-sheet behavior with an explicit full-list mode.
- Coordinate pointer hover, keyboard focus, list selection, map pin highlight, detail opening/closing, and URL-backed filters without replacing semantic controls with canvas-only interaction.
- Define focus entry/restoration for filters, result list, bottom sheet/drawer, detail, gallery, and close actions.
- Preserve controls, URL state, safe previous/list content, and status messaging through loading, empty, API error, tile/style error, and WebGL-unavailable states.
- Add automated accessibility checks and record a manual keyboard plus screen-reader/focus walkthrough at 360 px and desktop widths.

## Out of scope

- New filter, detail, media, masking, confidence, source-link, or backend semantics.
- Authentication/contact reveal/admin/restricted-action UX.
- Performance budgets, web-vitals instrumentation, metadata, or map-lifecycle optimization beyond regressions required for accessibility (E5-T5).

## Affected modules and contracts

- Map explorer layout, map/list/detail coordination, bottom sheet/full-list mode, semantic fallback/status UI, focus utilities, translations, responsive styles, and accessibility tests.
- Existing generated E4 query/detail contracts remain unchanged and backend-authoritative.

## Implementation notes

- The map canvas supplements rather than replaces the semantic result list and controls.
- Hover enhancement never gates selection; keyboard focus and activation provide equivalent behavior.
- Focus must not move on background query completion. Opening a modal drawer/sheet moves focus predictably; closing restores it to a still-present invoker or a defined list heading fallback.
- Announcements summarize state changes without reading every map movement or causing duplicate live-region noise.
- Reduced-motion preferences apply to sheet, highlight, map ease, and gallery transitions where supported.

## Acceptance criteria

- [x] Desktop presents a usable map/results/detail composition and 360 px presents a map-first bottom sheet plus full-list mode without horizontal overflow or obscured controls.
- [x] Hovering or focusing a result highlights its pin when present; keyboard selection opens the same content without requiring canvas interaction.
- [x] A keyboard-only user can set/clear filters, enter results, select a location and offer, inspect/close detail and gallery, switch mobile list mode, and open a verified source link.
- [x] Focus entry, containment where modal, and restoration are deterministic across drawer/sheet/detail/gallery open/close and remain valid when results refresh.
- [x] Loading, empty, API error, tile/style failure, and WebGL-unavailable states preserve filter controls and URL state, retain a useful semantic list where API data exists, and expose clear status/retry actions.
- [x] Visible focus, labels, names/descriptions, headings/landmarks, contrast, target sizing, status announcements, reduced motion, and non-color confidence/error cues meet the agreed WCAG 2.2 AA target.
- [x] Automated accessibility checks pass and a manual keyboard plus screen-reader/focus review is recorded for 360 px and desktop flows.

## Test plan

- Component: map/list highlight coordination, mobile mode/sheet, focus entry/restoration, result refresh, reduced motion, and every loading/empty/error/degraded state.
- Accessibility: automated axe-equivalent checks, role/name/state assertions, tab order, live-region deduplication, and no canvas-only operation.
- Browser/manual: keyboard-only and selected screen-reader walkthrough at 360 px and desktop widths; pointer hover parity; WebGL-disabled and tile/API failure probes.
- Regression: E5-T2 URL/filter lifecycle and E5-T3 detail/gallery behaviors remain intact.
- Repository: formatting, lint, typecheck, tests, production build, repository safety, and runtime image CI.

## Rollout and rollback

Web-only layout and interaction changes after E5-T2/E5-T3. Roll back the E5-T4 web commit/image to the prior detail-capable interface; no backend, data, or media rollback is required.

## Dependency blocker

- E5-T2 and E5-T3 must be complete before this task can be declared done.
- Under ADR-018, this task may become `ready` with `dependency_gate: stacked` only when both incomplete tasks are represented in direct ancestor PR order with branch, PR URL, and exact head commits recorded.

## Ready checklist

- [x] This file is authoritative under `tasks/`; no duplicate remains under `proposed-tasks/`.
- [x] Promotion, spike revision 3, and implementation-plan revision 3 are recorded.
- [ ] E5-T2 and E5-T3 are complete or valid direct ancestor PRs are recorded.
- [ ] Status moves to `ready` only after every gate is valid.

## Start checklist

- [ ] Status passed through `ready`.
- [ ] Dedicated E5-T4 branch is created from the green E5-T3 branch.
- [ ] Branch/PR contain E5-T4 only and metadata is recorded before `in_progress`.

## Done checklist

- [ ] Acceptance criteria pass.
- [ ] The global [definition of done](../../../workflow/DEFINITION_OF_DONE.md) passes.
- [ ] Dependency gate is `satisfied`; completion actor, time, pull request, and evidence are recorded.
