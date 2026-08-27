---
schema: ai-workflow/proposed-task@1
id: E14-T3
epic: E14
title: "Refactor frontend orchestration hotspots"
status: proposed
revision: 1
actionable: false
priority: P1
size: L
milestone: M5
dependencies: [E13-T3, E14-T2]
requirement_ids: [P-001, P-002, P-003, P-004, P-005, P-008]
decision_ids: [ADR-004, ADR-011, ADR-012, ADR-016]
deferred_decision_ids: []
source: "repository-audit:2026-08-26"
promotion:
  status: not_promoted
  target: null
  promoted_by: null
  promoted_at: null
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

## Promotion checklist

- [ ] E14 spike is explicitly owner-approved at its current revision.
- [ ] Scope, checks, dependencies, priority/size, and traceability match the approved spike.
- [ ] This file will be moved—not copied—to `tasks/` with complete promotion metadata.
