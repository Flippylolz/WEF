---
schema: ai-workflow/task@1
id: E20-T2
epic: E20
title: "Fix admin filter and form layout defects"
status: draft
revision: 1
priority: P1
size: M
milestone: M5
dependencies:
  - E20-T1
requirement_ids:
  - P-008
decision_ids:
  - ADR-012
  - ADR-016
deferred_decision_ids: []
promotion:
  source: ../proposed-tasks/E20-T2-admin-filter-form-layout-fixes.md
  promoted_by: "ZCode agent (owner-approved E20 planning under AD-044)"
  promoted_at: "2026-08-31T17:35:00Z"
spike_gate:
  status: satisfied
  file: ../SPIKE.md
  approved_revision: 1
  verified_by: "ZCode agent (AD-044)"
  verified_at: "2026-08-31T17:35:00Z"
implementation_gate:
  status: satisfied
  file: ../IMPLEMENTATION_PLAN.md
  approved_revision: 1
  verified_by: "ZCode agent (AD-045)"
  verified_at: "2026-08-31T17:40:00Z"
dependency_gate:
  status: blocked
  verified_by: null
  verified_at: null
  evidence: []
branch:
  required: true
  name: null
  task_id: E20-T2
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

# E20-T2: Fix admin filter and form layout defects

## Outcome

No `/admin` surface shows overlapping, crowded, or clipped controls: filter
rows, forms, tables, and inline action cells lay out cleanly at desktop and
narrow widths, with recorded before/after screenshots for each corrected page.

## Scope

- Catalogue the layout defects per surface with before screenshots on a
  running local stack: login, Users, Locations (list, filters, edit, point
  picker), Offer enrichment (batches and batch detail), Reveal audits, Admin
  audits.
- Fix the defects in the shared admin stylesheet from E20-T1: filter row
  wrapping for the six Location status tabs, spacing and alignment for form
  fields, table cell overflow handling, inline action forms in
  `admin-actions` cells, and the fixed-width Set-point evidence pane.
- Add responsive width handling where controls currently overlap or clip.
- Record after screenshots as completion evidence alongside the catalogue.

## Out of scope

- Color/token work (E20-T1 owns the palette; this task only consumes it).
- New admin functionality, additional views, or workflow changes.
- Public-site styling.

## Affected modules and contracts

- `apps/backend/src/wef_backend/features/admin/interface/` (views,
  enrichment views, shared stylesheet) only; no public/persisted contract,
  OpenAPI, database, or frontend changes. No migrations.

## Implementation notes

- Layout CSS in the shared admin stylesheet; minimal markup adjustments in the
  existing custom views where structure (not style) causes overlap.
- Keep changes backend-rendered and within the admin interface package per
  ADR-012/ADR-016; a material workflow or behavior change is a plan
  invalidation, not an in-task edit.
- Each fix is verifiable: the catalogue lists surface, defect, and the change
  that closes it; unit coverage asserts removed inline layout hacks stay
  removed where practical.
- Screenshot evidence must contain no real personal data (use seeded/local
  fixtures), consistent with the repository's no-personal-data rule.

## Acceptance criteria

- [ ] The documented catalogue shows before/after screenshots for every corrected surface, including narrow-viewport captures.
- [ ] Filter tabs, form fields, tables, and action buttons on all `/admin` pages render without overlap, truncation, or crowding at representative desktop and narrow widths.
- [ ] The Set-point evidence pane and map remain fully usable alongside each other at narrow widths.
- [ ] No per-page inline `<style>` layout blocks remain; styling lives in the shared stylesheet.
- [ ] Backend lint, type, and test checks pass; admin behavior, routes, and permissions are unchanged.

## Test plan

- Unit: absence of per-page inline `<style>` layout blocks in view HTML;
  presence of the shared layout classes the fixes rely on.
- Integration: admin list/form pages render the shared stylesheet and carry
  the corrected markup under existing admin test fixtures.
- Contract/migration: none required; assert no OpenAPI or schema changes.
- End-to-end: none automated (owner-only surface); before/after screenshots
  from the local stack are the recorded evidence.
- Security/accessibility/operations: no auth/route changes; no real personal
  data in evidence; responsive behavior verified at narrow widths.

## Rollout and rollback

- Ships with the normal backend release; no migration or configuration gate.
- Rollback is a `git revert` of the task PR; no persisted data or state is
  involved.

## Ready checklist

- [ ] The file is authoritative under `tasks/`; no duplicate remains under `proposed-tasks/`.
- [ ] Promotion source, promoter, and timestamp are recorded.
- [ ] `spike_gate` references the owner-approved current spike revision and is `satisfied`.
- [ ] `implementation_gate` references the owner-approved current implementation-plan revision, which contains this task ID/current revision, and is `satisfied`.
- [ ] Every dependency is `done` with `dependency_gate: satisfied`, or each incomplete dependency is an ancestor PR recorded by `dependency_gate: stacked`; every deferred gate is resolved.
- [ ] Scope and acceptance criteria match the approved plan.

## Start checklist

- [ ] Status passed through `ready`.
- [ ] One new branch contains this task ID.
- [ ] The branch and pull request contain this task only.
- [ ] `branch.name` and `branch.created_at` are recorded before setting `in_progress`.

## Done checklist

- [ ] Acceptance criteria pass.
- [ ] The global [definition of done](../../workflow/DEFINITION_OF_DONE.md) passes.
- [ ] Completion actor, time, pull request, and evidence are recorded.
