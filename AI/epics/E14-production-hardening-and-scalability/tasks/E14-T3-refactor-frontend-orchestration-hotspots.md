---
schema: ai-workflow/task@1
id: E14-T3
epic: E14
title: "Refactor frontend orchestration hotspots"
status: draft
revision: 1
priority: P1
size: L
milestone: M5
dependencies: [E13-T3, E14-T2]
requirement_ids: [P-001, P-002, P-003, P-004, P-005, P-008]
decision_ids: [ADR-004, ADR-011, ADR-012, ADR-016]
deferred_decision_ids: []
source: "repository-audit:2026-08-26"
promotion:
  source: ../proposed-tasks/E14-T3-refactor-frontend-orchestration-hotspots.md
  promoted_by: "Codex agent (owner-approved E14 planning under AD-041)"
  promoted_at: "2026-08-29T21:17:35Z"
spike_gate:
  status: satisfied
  file: ../SPIKE.md
  approved_revision: 1
  verified_by: "Codex agent (AD-041)"
  verified_at: "2026-08-29T21:17:35Z"
implementation_gate:
  status: blocked
  file: ../IMPLEMENTATION_PLAN.md
  approved_revision: null
  verified_by: null
  verified_at: null
dependency_gate:
  status: blocked
  verified_by: null
  verified_at: null
  evidence: []
branch:
  required: true
  name: null
  task_id: E14-T3
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

# E14-T3: Refactor frontend orchestration hotspots

## Outcome

Map, filter, selection, authentication, detail, and media UI behavior is organized into
small cohesive seams with explicit state ownership, while URL semantics, accessibility,
API contracts, and rendered behavior remain unchanged.

## Scope

- Characterize and then decompose `map-explorer.tsx`, `account-modal.tsx`,
  `offer-detail-drawer.tsx`, and their oversized tests along state/interaction boundaries.
- Separate URL/query derivation, selection/panel state, auth flows, contact reveal, and presentation without inventing a global client store.
- Preserve generated API types and TanStack Query as server-state authority.
- Consolidate repeated async/error/loading patterns where a concrete shared abstraction is clearer than duplication.
- Establish reviewed module/component complexity and bundle-diff budgets as regression signals, with justified exceptions rather than arbitrary line-count failures.

## Out of scope

- Visual redesign, new product behavior, backend rule duplication, new global state framework, map provider change, or general design-system rewrite.

## Acceptance criteria and checks

- [ ] Characterization tests prove identical URL serialization, filter application, map/list selection, modal/drawer focus, auth/contact/favorite flows, and error/empty/loading states before and after refactor.
- [ ] Each extracted seam has one clear owner and a narrow typed interface; cross-seam cycles are absent.
- [ ] No backend-owned visibility, authorization, grouping, masking, or filter rule is copied into frontend logic.
- [ ] Axe/component tests cover changed interactive surfaces and keyboard/focus behavior.
- [ ] Production build succeeds and the route's shipped JavaScript does not regress beyond an approved bundle budget.
- [ ] Format, lint, strict type, unit/component, coverage, accessibility, contract, build, and bundle-diff checks pass.

## Dependencies and gates

Depends on E13-T3 so the active redesign finishes before the same frontend seams are
refactored, and on E14-T2 so behavior is protected before structural changes.

## Risks and notes

Do not split files mechanically. Extract only stable responsibilities with tests; a
smaller file count is not acceptance evidence.

## Ready checklist

- [x] E14 spike revision 1 is owner-approved under AD-041.
- [x] E13-T3 is done and the task was promoted with complete metadata.
- [ ] E14 implementation plan revision 1 is owner-approved and E14-T2 is done.
