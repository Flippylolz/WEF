---
schema: ai-workflow/task@1
id: E20-T1
epic: E20
title: "Align admin console theme with the public dark design"
status: in_progress
revision: 1
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
promotion:
  source: ../proposed-tasks/E20-T1-admin-dark-theme-alignment.md
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
  status: satisfied
  verified_by: "ZCode agent (AD-044)"
  verified_at: "2026-08-31T17:35:00Z"
  evidence: []
branch:
  required: true
  name: feat/E20-T1-admin-dark-theme-alignment
  task_id: E20-T1
  one_task_only: true
  created_at: "2026-08-31T17:45:00Z"
  pull_request: "https://github.com/Flippylolz/WEF/pull/247"
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

## Affected modules and contracts

- `apps/backend/src/wef_backend/features/admin/interface/` (mount, views,
  enrichment views, statics) only; no public/persisted contract, OpenAPI,
  database, or frontend changes. No migrations.

## Implementation notes

- Backend-rendered styling only, consistent with ADR-012/ADR-016: the
  stylesheet and any minimal `templates_dir` override live in the admin
  interface package.
- Contrast of text, borders, and state colors must remain legible in dark mode
  on every converted page, including map-picker controls and AI diff tables.
- If a Tabler 1.4.0 variable cannot be mapped through the shared stylesheet, a
  minimal `templates_dir` override is the recorded fallback; a larger template
  fork is a material deviation requiring plan revision.
- Unit coverage asserts the shared stylesheet is wired (served) and the
  hardcoded light declarations are gone; visual confirmation is recorded as
  task evidence.

## Acceptance criteria

- [ ] `/admin` (login, list pages, filters, forms, detail, custom views) renders dark with the Primer-aligned palette and no mixed light body/dark sidebar inconsistency.
- [ ] Set-point, Review-with-AI, and enrichment pages use `color-scheme: dark`, the shared tokens, and contain no hardcoded `#ffffff`/`#fff` page backgrounds.
- [ ] One shared stylesheet is the only place admin color tokens are defined; no new per-page `<style>` color blocks are introduced.
- [ ] `place_picker.js` point placement works with unchanged coordinate behavior.
- [ ] Backend lint, type, and test checks pass; no frontend or contract changes are required.

## Test plan

- Unit: mount/theme configuration; shared stylesheet served under `/admin`
  statics; absence of hardcoded light declarations in view HTML.
- Integration: admin pages render with the dark theme attributes under the
  owner auth provider (existing admin test fixtures).
- Contract/migration: none required; assert no OpenAPI or schema changes.
- End-to-end: none (owner-only surface); manual visual pass recorded as
  evidence.
- Security/accessibility/operations: no auth/route changes; dark-palette
  contrast spot checks; no new configuration.

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
- [ ] The global [definition of done](../../../workflow/DEFINITION_OF_DONE.md) passes.
- [ ] Completion actor, time, pull request, and evidence are recorded.
