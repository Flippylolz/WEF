---
schema: ai-workflow/proposed-task@1
id: E20-T1
epic: E20
title: "Align admin console theme with the public dark design"
status: proposed
revision: 1
actionable: false
priority: P1
size: M
milestone: M5
dependencies: []
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

# E20-T1: Align admin console theme with the public dark design

## Outcome

Every `/admin` surface — Tabler shell, custom views, and the standalone
Set-point, Review-with-AI, and enrichment pages — renders in the public
website's GitHub Dark (Primer) palette and Inter typography with a single
shared admin stylesheet, and the hardcoded per-page light styles are removed.

## Scope

- Activate Starlette Admin's supported dark mode (`TablerSettings(mode="dark")`
  or equivalent) in `build_admin`.
- Add one shared admin stylesheet served through the console's existing
  `statics` mount that maps Tabler/Bootstrap CSS variables onto the public
  tokens from `apps/web/src/app/globals.css` (canvas `#0d1117`, surfaces
  `#161b22`/`#21262d`, border `#30363d`, text `#e6edf3`, muted `#8b949e`,
  accents `#3fb950`/`#238636`, focus `#4493f8`, warning `#d29922`, danger
  `#f85149`).
- Convert the three standalone light pages (Set-point picker, Review-with-AI,
  enrichment batches) to the shared tokens, replacing their inline
  `<style>` blocks and `color-scheme: light` declarations.
- Keep `place_picker.js` behavior unchanged; only its palette/contrast changes.

## Out of scope

- Fixing layout/overlap defects beyond what token application requires
  (E20-T2).
- Any change to admin behavior, routes, permissions, audits, or the public
  site.
- Replacing or heavily overriding packaged `starlette-admin` templates.

## Work

- Backend-rendered styling only, consistent with ADR-012/ADR-016: the
  stylesheet and minimal template/static overrides live in the admin interface
  package.
- Contrast of text, borders, and state colors must remain legible in dark mode
  on every converted page, including map-picker controls and AI diff tables.
- Unit coverage asserts the shared stylesheet is wired (served) and the
  hardcoded light declarations are gone; visual confirmation is recorded as
  task evidence.

## Acceptance criteria

- [ ] `/admin` (login, list pages, filters, forms, detail, custom views) renders dark with the Primer-aligned palette and no mixed light body/dark sidebar inconsistency.
- [ ] Set-point, Review-with-AI, and enrichment pages use `color-scheme: dark`, the shared tokens, and contain no hardcoded `#ffffff`/`#fff` page backgrounds.
- [ ] One shared stylesheet is the only place admin color tokens are defined; no new per-page `<style>` color blocks are introduced.
- [ ] `place_picker.js` point placement works with unchanged coordinate behavior.
- [ ] Backend lint, type, and test checks pass; no frontend or contract changes are required.

## Dependencies and gates

- No task dependencies. Promotion additionally requires the epic spike
  approval (revision 1 or later) and, after promotion, the implementation-plan
  gate per the workflow.

## Risks and notes

- Tabler 1.4.0 variable names for accent/focus mapping are confirmed during
  implementation; if a variable cannot be mapped, a minimal `templates_dir`
  override is the fallback recorded in the spike.
- Future `starlette-admin` upgrades may shift packaged styling; the task
  records a visual re-verification step for upgrades.

## Promotion checklist

- [ ] The epic spike is explicitly owner-approved for its current revision.
- [ ] Scope, acceptance, dependencies, priority, size, and traceability match the approved spike.
- [ ] Required deferred decisions are resolved.
- [ ] The file will be moved—not copied—to the epic's `tasks/`.
- [ ] Promotion metadata will identify the target, promoter, and timestamp.
