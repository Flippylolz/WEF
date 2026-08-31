---
schema: ai-workflow/proposed-task@1
id: E20-T2
epic: E20
title: "Fix admin filter and form layout defects"
status: proposed
revision: 1
actionable: false
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
source: null
promotion:
  status: not_promoted
  target: null
  promoted_by: null
  promoted_at: null
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

## Work

- Layout CSS in the shared admin stylesheet; minimal markup adjustments in the
  existing custom views where structure (not style) causes overlap.
- Keep changes backend-rendered and within the admin interface package per
  ADR-012/ADR-016.
- Each fix is verifiable: the catalogue lists surface, defect, and the change
  that closes it; unit coverage asserts removed inline layout hacks stay
  removed where practical.

## Acceptance criteria

- [ ] The documented catalogue shows before/after screenshots for every corrected surface, including narrow-viewport captures.
- [ ] Filter tabs, form fields, tables, and action buttons on all `/admin` pages render without overlap, truncation, or crowding at representative desktop and narrow widths.
- [ ] The Set-point evidence pane and map remain fully usable alongside each other at narrow widths.
- [ ] No per-page inline `<style>` layout blocks remain; styling lives in the shared stylesheet.
- [ ] Backend lint, type, and test checks pass; admin behavior, routes, and permissions are unchanged.

## Dependencies and gates

- Task dependency `E20-T1`: layout fixes build on the shared stylesheet and
  dark tokens it introduces. Promotion additionally requires the epic spike
  approval and, after promotion, the implementation-plan gate per the
  workflow.

## Risks and notes

- The precise defect inventory is owner-reported plus code-derived until the
  before screenshots exist; the catalogue step is deliberately first so scope
  stays bounded to observed defects.
- Screenshot evidence must contain no real personal data (use seeded/local
  fixtures), consistent with the repository's no-personal-data rule.

## Promotion checklist

- [ ] The epic spike is explicitly owner-approved for its current revision.
- [ ] Scope, acceptance, dependencies, priority, size, and traceability match the approved spike.
- [ ] Required deferred decisions are resolved.
- [ ] The file will be moved—not copied—to the epic's `tasks/`.
- [ ] Promotion metadata will identify the target, promoter, and timestamp.
