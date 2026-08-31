---
schema: ai-workflow/spike@1
epic: E20
title: "Admin console visual refresh research"
status: awaiting_approval
revision: 1
owner: owner
research_only: true
code_allowed: false
decision_ids:
  - ADR-012
  - ADR-016
domain_docs:
  - ../../product/EXPERIENCE.md
  - ../../security/AUTH_ADMIN_CONTACTS.md
proposed_task_ids:
  - E20-T1
  - E20-T2
approval:
  required_role: owner
  status: pending
  decided_by: null
  decided_at: null
  approved_revision: null
  evidence: null
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# Spike: Admin console visual refresh research

## Question

How can the owner-only Starlette Admin console at `/admin` adopt the public
website's GitHub Dark (Primer) visual language and eliminate overlapping or
crowded filters, forms, and tables, without changing admin behavior, security
boundaries, or introducing a new frontend stack?

## Context and constraints

- The console is a backend-rendered owner surface secured by the owner auth
  provider and mutation guard
  (`apps/backend/src/wef_backend/features/admin/interface/mount.py`,
  `auth.py`, `guards.py`); ADR-012 keeps business behavior
  backend-authoritative and ADR-016 defines the owner console boundary.
  Remaining backend-rendered is an accepted constraint of this research.
- The public site's palette is the documented GitHub Dark (Primer) token set in
  `apps/web/src/app/globals.css`: canvas `#0d1117`, subtle `#161b22`, raised
  `#21262d`, border `#30363d`, text `#e6edf3`, muted `#8b949e`, green
  `#3fb950`/`#238636`, blue `#4493f8`, attention `#d29922`, danger `#f85149`,
  with Inter and `color-scheme: dark`.
- The locked dependency is `starlette-admin` 1.0.0 (`apps/backend/uv.lock`);
  research on its theming API used the installed package sources only.
- Spike work is documentation-only: no stylesheets, templates, or Python were
  changed, and no disposable proof code was written. The exact visual defect
  catalogue therefore remains owner-reported plus code-derived until
  implementation captures screenshots.

## Research method

- Read the admin interface sources under
  `apps/backend/src/wef_backend/features/admin/interface/` and the public
  design tokens in `apps/web/src/app/globals.css`.
- Read the installed `starlette_admin` 1.0.0 package (`theme.py`, `base.py`,
  `templates/`) to verify supported theming and override points.
- Cross-checked the owner-reported overlap symptom against the page structure
  in the custom views to identify structural causes in code.

## Evidence

Verified facts:

- `build_admin` constructs `BaseAdmin` without a `theme` argument, so the
  console uses the default Tabler `mode="light"` page body while the packaged
  `layout.html` (line 9) hardcodes `data-bs-theme="dark"` on the sidebar — the
  console already mixes light content with a dark sidebar.
- `starlette_admin` 1.0.0 natively supports the target look:
  - `TablerSettings(mode="light" | "dark")` renders `data-bs-theme` on
    `<html>` (`theme.py`, `TablerSettings.html_attrs`), switching Tabler 1.4.0
    (`css/vendor/tabler.min.css`, loaded in `base.html`) color schemes.
  - `BaseAdmin(templates_dir=...)` checks a custom template directory before
    the packaged ones (`base.py`), and the console already mounts a custom
    `statics/` directory (currently only `place_picker.js`).
  - The packaged fonts block already imports Inter, matching the public site's
    type family.
- Three standalone pages hardcode light styling inside Python string HTML and
  bypass the Tabler shell entirely:
  - Set-point map picker (`views.py`, `_point_picker_page` region):
    `html{color-scheme:light}`, `background:#ffffff`, fixed-width
    `#evidence{width:360px}` pane.
  - Review-with-AI page (`views.py`): `background:#fff`, hand-built tables.
  - Offer-enrichment batch pages (`enrichment_views.py`): `background:#fff`,
    plus the only shared layout rule in the console,
    `.admin-actions form{display:inline}`.
- Structural overlap causes in the custom views: per-page inline `<style>`
  blocks (three sites) instead of a shared stylesheet, inline action forms
  packed into `<td class='admin-actions'>` cells, six Location filter tabs
  rendered as a flat row, and table/form markup with no responsive width
  handling. These match the owner-reported overlapping filters and fields;
  the per-page visual catalogue (which surface, which control, which
  breakpoint) is pending implementation-time screenshots and is the only
  unverified evidence in this spike.

Assumptions:

- Tabler 1.4.0's `data-bs-theme="dark"` plus a CSS-variable override layer is
  sufficient to reach a visually consistent Primer-aligned palette; exact
  Tabler variable names are confirmed during implementation.
- Darkening the map picker's canvas background does not affect its coordinate
  math; `place_picker.js` behavior is regression-checked, not redesigned.

## Options considered

1. **Tabler dark mode + shared token stylesheet (selected).** Enable
   `mode="dark"`, ship one admin stylesheet mapping Tabler/Bootstrap CSS
   variables to the public Primer tokens, and convert the three standalone
   pages to the same tokens; fix layout defects in the same stylesheet.
   Benefits: uses supported library extension points; single source of styling
   truth; smallest regression surface; reversible. Costs: a CSS-variable
   mapping layer to maintain across `starlette-admin` upgrades. Risks: upgrade
   drift in packaged templates/variables (mitigated by the lockfile and
   override verification).
2. **Override packaged templates wholesale.** Copy and edit Tabler templates
   via `templates_dir`. Rejected as the primary approach: large diff surface
   that must be re-validated on every library upgrade; only needed if a
   specific template blocks token mapping, and then minimally.
3. **Replace Starlette Admin with a custom admin frontend.** Rejected: high
   cost, new public attack surface and contract work, contradicts the
   backend-rendered owner console boundary under ADR-012/ADR-016, and the
   owner-only audience does not justify it.
4. **Keep light theme, restyle accents only.** Rejected: does not satisfy the
   owner's requirement that the console match the public site's dark design.

## Recommendation

Adopt option 1. Consequences: the console's visual language becomes a
first-class, centrally-owned stylesheet aligned with the public Primer tokens;
`starlette-admin` upgrades require a short visual re-verification recorded in
the epic; the three standalone pages lose their hardcoded light styles.
No new decisions are required; ADR-012/ADR-016 already cover the backend-
rendered console, and no deferred decision gates this work.

## Proposed task boundaries

- **E20-T1 — Align admin console theme with the public dark design** (P1/M):
  dark-mode activation, the shared token stylesheet wired through the existing
  `statics`/`templates_dir` override points, conversion of the Set-point,
  Review-with-AI, and enrichment pages to the shared tokens, and removal of
  the hardcoded light styles. No layout-defect fixing beyond what token
  application requires.
- **E20-T2 — Fix admin filter and form layout defects** (P1/M, depends on
  E20-T1): per-view catalogue with before screenshots (Users, Locations incl.
  point picker, Offer enrichment, Reveal/Admin audits, login), then
  spacing/wrapping/overflow fixes for filter rows, forms, tables, and action
  cells in the shared stylesheet, with after screenshots as completion
  evidence.

## Risks and open questions

- **Library upgrade drift** — packaged templates or CSS variables may change
  in future `starlette-admin` releases. Mitigation: lockfile plus a recorded
  visual re-verification step after upgrades.
- **Unverified exact defect catalogue** — the overlap inventory is
  owner-reported plus code-derived. Closed by E20-T2's before screenshots on a
  running local stack.
- **Dark-palette regressions in bespoke widgets** — the map picker and AI
  review diff tables need contrast/legibility checks in dark mode.
- **Owner-only surface has thin automated coverage** — visual checks rely on
  unit tests for removed inline styles plus owner verification of the deployed
  console.
- Open question: exact Tabler 1.4.0 variable names for accent/focus mapping —
  confirmed during E20-T1 implementation; does not change scope.

## Invalidation triggers

- The public design tokens (Primer palette, E13 shell) change materially.
- A `starlette-admin` major upgrade replaces the Tabler theming API assumed
  here.
- The owner decides to move administration into a separate frontend.
- New admin views or workflows materially change the surface list above.

## Exit checklist

- [x] The question is answered within the stated scope.
- [x] Evidence and uncertainty are distinguishable.
- [x] Affected decisions and domain documents are linked.
- [x] Proposed task boundaries and dependencies are identified.
- [x] No production or disposable proof code was created.
- [x] `revision` represents the material content being submitted.
- [x] `status` is `awaiting_approval` and approval remains `pending`.

## Owner decision

The owner records the decision only in the YAML `approval` object. Approval of
this spike revision permits task refinement/promotion and implementation
planning; it does not permit code.
