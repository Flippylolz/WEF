---
schema: ai-workflow/epic@1
id: E20
title: "Admin console visual refresh"
status: planning
milestones: [M5]
owner: owner
spike: SPIKE.md
implementation_plan: IMPLEMENTATION_PLAN.md
---

# E20: Admin console visual refresh

## Outcome

The owner-only Starlette Admin console at `/admin` shares the public website's
visual language: the GitHub Dark (Primer) palette, Inter typography, and a
consistent dark color scheme across the Tabler shell, every custom view, and
the standalone Set-point, Review-with-AI, and offer-enrichment pages. Filters,
forms, tables, and action rows render from one shared admin stylesheet, so
controls no longer overlap or crowd each other, and each corrected surface has
recorded before/after evidence.

## Current state (verified in code)

- `build_admin` mounts `BaseAdmin` with default theming, so the console renders
  Tabler's light mode while the packaged layout hardcodes a dark sidebar — a
  mixed appearance already visible today
  (`apps/backend/src/wef_backend/features/admin/interface/mount.py`).
- The public site defines the target palette as CSS custom properties in
  `apps/web/src/app/globals.css` (`--background: #0d1117`, `--surface:
  #161b22`, `--border: #30363d`, `--foreground: #e6edf3`, `--accent: #3fb950`,
  `--focus: #4493f8`, Inter, `color-scheme: dark`).
- Admin pages carry hand-rolled inline `<style>` blocks in Python strings —
  Set-point (`views.py`), Review-with-AI (`views.py`), and enrichment
  (`enrichment_views.py`) hardcode light backgrounds (`background: #ffffff`,
  `color-scheme: light`) that clash with both the Tabler shell and the public
  site.
- Layout styling is ad hoc: fixed-width panes (for example the 360px evidence
  pane in the Set-point page), inline action forms in table cells, six filter
  tabs, and only one shared layout rule (`.admin-actions form{display:inline}`).
  The owner reports overlapping filters and fields; the code shows structural
  causes, and the exact per-page defect catalogue is captured with screenshots
  at the start of implementation.
- `starlette-admin` 1.0.0 (locked) natively supports dark mode via
  `TablerSettings(mode="dark")` (`data-bs-theme` on `<html>`), template
  overrides through `templates_dir`, and custom static files — the console
  already ships a `statics/` directory.

## Direction

Enable Tabler's dark mode for the admin, add one shared admin stylesheet that
maps the Tabler/Bootstrap CSS variables onto the public Primer tokens, convert
the three standalone light pages to the shared tokens, and then fix the
filter/form/table layout defects in that stylesheet with per-view before/after
evidence. The console remains a backend-rendered owner surface; no new frontend
framework or public-facing change is introduced.

## Milestones

[M5](../../milestones/M5-production-maturity.md)

## Governing documents

- [P-008: Registration and contact reveal](../../product/EXPERIENCE.md#p-008-registration-and-contact-reveal)
- [Authentication, administration, and contact reveal](../../security/AUTH_ADMIN_CONTACTS.md)

## Governing decisions

- [ADR-012](../../decisions/adr/ADR-012-backend-centric-modular-monolith.md)
- [ADR-016](../../decisions/adr/ADR-016-pseudonymous-accounts-owner-console.md)

## Promoted tasks

- [E20-T1: Align admin console theme with the public dark design](tasks/E20-T1-admin-dark-theme-alignment.md) — promoted/`draft`, P1/M, M5
- [E20-T2: Fix admin filter and form layout defects](tasks/E20-T2-admin-filter-form-layout-fixes.md) — promoted/`draft`, P1/M, M5

## Approval state

- Epic workspace status: `planning`.
- `SPIKE.md` revision 1 was owner-approved on 2026-08-31 under AD-044
  (owner directive recorded in the [autonomous decision
  log](../../workflow/AUTONOMOUS_DECISIONS.md)).
- [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) revision 1 awaits owner
  approval; E20-T1/E20-T2 remain `draft` and non-actionable until that gate
  clears.
