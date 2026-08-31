---
schema: ai-workflow/implementation-plan@1
epic: E20
title: "Admin console visual refresh implementation plan"
status: awaiting_approval
revision: 1
owner: owner
spike_revision: 1
task_sequence:
  - id: E20-T1
    revision: 1
  - id: E20-T2
    revision: 1
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

# Implementation Plan: Admin console visual refresh

## Approved spike baseline

- [E20 SPIKE.md](SPIKE.md) revision 1, owner-approved 2026-08-31 under
  AD-044 (evidence recorded in its YAML `approval` object).
- `spike_revision: 1` remains current: no token, surface, library, or
  recommendation premise has changed since approval.
- Binding constraints from the spike: remain on locked `starlette-admin`
  1.0.0 with its supported theming/override points (`TablerSettings`,
  `statics`, minimal `templates_dir` use only as fallback); one shared admin
  stylesheet mapping the public Primer tokens from
  `apps/web/src/app/globals.css`; no admin behavior, permission, route, or
  public-site changes; ADR-012/ADR-016 boundary preserved.

## Scope and outcome

- Outcome (epic README): the owner-only `/admin` console shares the public
  GitHub Dark visual language across the Tabler shell, every custom view, and
  the three standalone pages, and filters/forms/tables/action rows render from
  the shared stylesheet without overlap, with before/after evidence.
- Included: dark-mode activation, the shared token stylesheet, conversion of
  the Set-point/Review-with-AI/enrichment pages, per-view layout-defect
  catalogue and repairs, responsive width handling, screenshot evidence.
- Exclusions: admin functionality/workflows, public site, new dependencies,
  packaged-template forking, and any frontend application change.

## Ordered task sequence

### 1. [E20-T1](tasks/E20-T1-admin-dark-theme-alignment.md) — revision 1

- Independently reviewable: delivers the complete dark Primer-aligned palette
  on every admin surface without touching layout behavior.
- Dependencies: none. `dependency_gate: satisfied` recorded at promotion.
- Affected modules/contracts:
  `apps/backend/src/wef_backend/features/admin/interface/` (mount, views,
  enrichment views, statics); no contracts, OpenAPI, or migrations.
- Tests/risks/rollout: unit checks for theme configuration, served stylesheet,
  and removed light declarations; integration render checks with admin
  fixtures; manual visual pass. Ships with a normal release; rollback is
  reverting the PR. Main risk — unmappable Tabler variables (fallback:
  minimal `templates_dir` override) and dark-contrast regressions in the map
  picker/AI diff tables.

### 2. [E20-T2](tasks/E20-T2-admin-filter-form-layout-fixes.md) — revision 1

- Independently reviewable: the catalogue-then-fix pass for overlaps and
  crowding, on top of the T1 stylesheet, with screenshot evidence.
- Dependencies: `E20-T1` must be `done`; its merged PR is the dependency-gate
  evidence (stacked branching may develop T2 against the T1 branch, merging
  base-first).
- Affected modules/contracts: same admin interface package (views markup
  minimally, shared stylesheet primarily); no contracts or migrations.
- Tests/risks/rollout: unit checks that inline `<style>` layout blocks stay
  removed; integration render checks; before/after screenshots from the local
  stack (seeded fixtures only, no real personal data) as recorded evidence.
  Rollback is reverting the PR. Main risk — the defect inventory grows during
  cataloguing; scope stays bounded to observed defects, and material scope
  growth returns to this plan.

## Cross-task architecture

- Dependency direction: T1 produces the single shared stylesheet and theme
  activation; T2 only consumes them. No shared domain/application rules are
  duplicated; both tasks confine changes to the admin interface package
  (presentation only), keeping behavior in the admin application services.
- No transaction, persistence, or generated-contract surface is touched; both
  tasks are backend-rendered presentation changes under ADR-012.

## Data and migrations

- None. No schema, data, or migration changes; rollback restores the prior
  rendering and cannot lose data by construction.

## Security and privacy

- No authentication, authorization, session, audit, or route changes: the
  owner auth provider and mutation guard middleware remain untouched, and the
  shared stylesheet is served only through the authenticated `/admin` statics
  mount.
- Evidence screenshots are taken against seeded local fixtures; no real
  personal data, raw exports, or production media enter Git or evidence
  (repository data rules).

## Test and verification strategy

- Unit (both tasks): theme configuration, stylesheet wiring, absence of
  hardcoded light styles and inline `<style>` blocks in view HTML.
- Integration: admin pages render with dark theme attributes and the shared
  stylesheet using existing owner-auth admin test fixtures.
- Contract/migration: explicit assertion that no OpenAPI/schema changes occur.
- Visual/operational: T2's before/after screenshot catalogue (desktop and
  narrow widths) is the acceptance evidence; `make lint`, `make typecheck`,
  and `make test` run per repository rules on each task PR.

## Operations, rollout, and rollback

- Rollout: one dedicated branch/PR per task in dependency order
  (`feat/E20-T1-...`, then `feat/E20-T2-...`), merged base-first after green
  required CI; the production deploy workflow ships the console with the next
  release; verify `/admin` serving and login after deploy.
- Rollback: `git revert` the offending task PR and redeploy; no data recovery
  is involved.
- Host non-interference: no infrastructure, compose, or shared-edge changes.

## Risks and mitigations

- Tabler 1.4.0 variable mapping gaps (T1) — mitigate with the spike-recorded
  minimal `templates_dir` fallback; escalate to plan revision if larger.
- Dark-mode contrast regressions in bespoke widgets: map picker and AI diff
  tables (T1) — dedicated contrast spot checks plus the recorded visual pass.
- `starlette-admin` upgrade drift (post-completion) — lockfile plus a visual
  re-verification step recorded in the epic on upgrades.
- Defect-catalogue growth mid-task (T2) — catalogue step first; scope bounded
  to observed defects; material growth returns to this plan.
- Owner-only surface with thin automated coverage (both) — unit/integration
  assertions plus owner verification of the deployed console recorded as
  completion evidence.

## Invalidation triggers

- The public design tokens (Primer palette, E13 shell) change materially.
- A `starlette-admin` upgrade replaces the theming API assumed here.
- New admin views/workflows materially change the surface list.
- Any material deviation discovered during implementation (behavior, new
  dependency, template fork) stops work and returns to this plan or the spike
  per the global invalidation rules.

## Approval checklist

- [x] The referenced spike revision has explicit owner approval and remains valid.
- [x] Every sequence entry is a promoted task with complete acceptance criteria and traceability.
- [x] Dependencies are complete, acyclic, and enforceable task by task.
- [x] Affected modules, contracts, tests, migrations, risks, rollout, and rollback are explicit.
- [x] Deferred decisions required for implementation are resolved (none apply).
- [x] No production or disposable proof code has been written.
- [x] `revision` represents the material plan being submitted.
- [x] `status` is `awaiting_approval` and approval remains `pending`.

## Owner decision

The owner records the decision only in the YAML `approval` object. Approval
authorizes the recorded plan revision, not blanket epic implementation: each
task must still satisfy promotion, dependency, state, and one-branch-per-task
gates.
