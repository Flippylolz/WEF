---
schema: ai-workflow/task@1
id: E18-T2
epic: E18
title: "Location admin console page and map picker"
status: draft
revision: 1
priority: P1
size: M
milestone: M5
dependencies:
  - E18-T1
requirement_ids:
  - P-008
decision_ids:
  - ADR-012
  - ADR-016
  - ADR-021
deferred_decision_ids: []
promotion:
  source: ../proposed-tasks/E18-T2-location-admin-console.md
  promoted_by: "ZCode agent under owner instruction"
  promoted_at: "2026-08-30T11:03:58Z"
spike_gate:
  status: satisfied
  file: ../SPIKE.md
  approved_revision: 1
  verified_by: "ZCode agent under owner instruction"
  verified_at: "2026-08-30T11:03:58Z"
implementation_gate:
  status: satisfied
  file: ../IMPLEMENTATION_PLAN.md
  approved_revision: 1
  verified_by: "ZCode agent under owner instruction"
  verified_at: "2026-08-30T11:03:58Z"
dependency_gate:
  status: blocked
  verified_by: null
  verified_at: null
  evidence: []
branch:
  required: true
  name: null
  task_id: E18-T2
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

# E18-T2: Location admin console page and map picker

## Outcome

The owner console gains a "Locations" page at `/admin/places` where the owner
filters and searches every location, opens a full-page map picker showing the
location's offer data, and places, accepts, rejects, or re-opens the location's
point — every action guarded, lineage-tracked, and audit-logged through E18-T1's
service.

## Scope

- `LocationsAdminView` (`features/admin/interface/views.py`, menu "Locations",
  path `/places`): status filter links (pending default, accepted, rejected,
  ungeocoded, needs_review, all), address search box, 100-row table with per-row
  actions "Edit point", "Accept candidate" (only when an in-scope candidate
  exists), "Reject", and "Unresolve" (only for decided locations).
- Full-page set-point picker route (`GET /admin/places/set-point`): standalone
  HTML document with the location's offer evidence (address, district, latest
  offer excerpts, price/area/rooms, visibility, published), candidate details,
  an error banner slot, and a vanilla-JS slippy map (OSM raster tiles, drag pan,
  zoom controls, double-click zoom, click-to-place marker, editable lat/lng
  inputs) served from the admin `static_dir`.
- POST routes (`set-point`, `accept`, `reject`, `unresolve`) with `csrf_input`,
  303 redirects back to the list or picker, and error-banner redirect-back on
  validation failure.
- `build_admin` wiring of a package-relative static directory; view registration.
- Admin HTTP tests; `AI/` documentation updates (security, architecture,
  geocoding semantics); task completion records and epic status updates.

## Out of scope

- Backend service behavior beyond what E18-T1 delivered (bug fixes to it would be
  a material plan change).
- Public API, frontend web app, OpenAPI contract, migrations.
- Bulk operations, pagination, non-coordinate field editing, re-geocoding
  triggers.

## Affected modules and contracts

- `apps/backend/src/wef_backend/features/admin/interface/views.py`
- `apps/backend/src/wef_backend/features/admin/interface/mount.py`
- `apps/backend/src/wef_backend/features/admin/interface/statics/place_picker.js`
  (new)
- `apps/backend/src/wef_backend/app.py` (build_admin call site, if needed)
- `apps/backend/tests/test_admin_api.py` (or sibling admin HTTP test module)
- `AI/security/AUTH_ADMIN_CONTACTS.md`, `AI/architecture/SYSTEM.md`,
  `AI/ingestion/GEOCODING.md`, `AI/epics/README.md`, epic README/tasks

## Implementation notes

- The picker page is a full standalone HTML response (not an admin-layout widget)
  so its script executes on normal navigation; the static script is served from
  `/admin/static/...` via starlette-admin's `static_dir` (checked before built-in
  assets).
- The picker prefiles from the existing point, then the candidate point, then the
  district centroid, then the Warsaw center; existing and candidate positions are
  distinguishable markers.
- All mutations are POST forms carrying `csrf_input`; failures redirect back to
  the picker with an error banner (no silent `AdminDeniedError` swallowing on
  owner-facing pages).
- No new package dependencies; tiles are fetched by the owner's browser from OSM
  with attribution links shown on the page.

## Acceptance criteria

- [ ] The list renders for every status filter and a search term, with filter
  state visible and re-clickable, defaulting to the pending queue.
- [ ] The picker page shows the location's offer evidence, candidate details, map
  holder, lat/lng inputs, CSRF form, and script tag; unknown ids redirect back
  with an error.
- [ ] Each POST route performs its transition through `AdminService` and
  redirects 303; invalid/out-of-scope input lands back on the picker with a
  visible error and changes nothing.
- [ ] Missing CSRF or cross-origin mutation posts are rejected by the existing
  guard; a non-owner cannot reach the page (login flow).
- [ ] `AI/` documentation describes the new page, its audit actions, and the
  manual-placement semantics; epic/task records are updated.
- [ ] Admin HTTP tests pass; `make lint`, `make format-check`, `make typecheck`,
  `make test` pass.

## Test plan

- Unit: n/a beyond E18-T1 fakes reused for composition.
- Integration: n/a new (E18-T1 covers store behavior).
- Contract/migration: `make contract-check` stays green; no migration.
- HTTP: `tests/test_admin_api.py`-style tests driving the real app with fake
  services (CSRF scrape helpers) covering list/picker/actions/guards.
- End-to-end/manual: browser verification of the picker against the local stack
  and, after merge, against production behind owner login.
- Security/accessibility: owner-only gating, CSRF/origin negatives, labeled
  form controls, error banners reachable by keyboard.

## Rollout and rollback

- Static asset ships in the backend image; standard deploy, then production
  verification of `/admin` and `/admin/places`. Rollback is revert + redeploy; no
  data rollback exists or is needed.

## Ready checklist

- [x] The file is authoritative under `tasks/`; no duplicate remains under
  `proposed-tasks/`.
- [x] Promotion source, promoter, and timestamp are recorded.
- [x] `spike_gate` references the owner-approved current spike revision and is
  `satisfied`.
- [x] `implementation_gate` references the owner-approved current
  implementation-plan revision, which contains this task ID/current revision, and
  is `satisfied`.
- [ ] Every dependency is `done` with `dependency_gate: satisfied` (E18-T1
  pending) or recorded as stacked; every deferred gate is resolved.
- [x] Scope and acceptance criteria match the approved plan.

## Start checklist

- [ ] Status passed through `ready`.
- [ ] One new branch contains this task ID.
- [ ] The branch and pull request contain this task only.
- [ ] `branch.name` and `branch.created_at` are recorded before setting
  `in_progress`.

## Done checklist

- [ ] Acceptance criteria pass.
- [ ] The global [definition of done](../../workflow/DEFINITION_OF_DONE.md) passes.
- [ ] Completion actor, time, pull request, and evidence are recorded.
