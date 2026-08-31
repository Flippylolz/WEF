---
schema: ai-workflow/task@1
id: E19-T2
epic: E19
title: "Owner AI place-review console and production controls"
status: done
revision: 3
priority: P0
size: M
milestone: M5
dependencies:
  - E19-T1
requirement_ids:
  - P-009
decision_ids:
  - ADR-012
  - ADR-016
  - ADR-022
deferred_decision_ids: []
promotion:
  source: ../proposed-tasks/E19-T2-ai-place-review-console.md
  promoted_by: "Cursor Agent (owner-directed E19 mission under AD-042/AD-043)"
  promoted_at: "2026-08-30T21:36:00Z"
spike_gate:
  status: satisfied
  file: ../SPIKE.md
  approved_revision: 4
  verified_by: "Cursor Agent (AD-042)"
  verified_at: "2026-08-30T21:36:00Z"
implementation_gate:
  status: satisfied
  file: ../IMPLEMENTATION_PLAN.md
  approved_revision: 1
  verified_by: "Cursor Agent (AD-043)"
  verified_at: "2026-08-30T21:36:00Z"
dependency_gate:
  status: satisfied
  verified_by: "Cursor Agent (owner-directed E19 mission under AD-042/AD-043)"
  verified_at: "2026-08-30T23:20:00Z"
  evidence:
    - "E19-T1 merged through https://github.com/Flippylolz/WEF/pull/226 (1120312)"
branch:
  required: true
  name: feat/E19-T2-ai-place-review-console
  task_id: E19-T2
  one_task_only: true
  created_at: "2026-08-30T23:20:00Z"
  pull_request: "https://github.com/Flippylolz/WEF/pull/227"
completion:
  completed_by: "Cursor Agent (owner-directed E19 mission under AD-042/AD-043)"
  completed_at: "2026-08-30T23:45:00Z"
  pull_request: "https://github.com/Flippylolz/WEF/pull/227"
  evidence:
    - "Merged as d8673dc on main through https://github.com/Flippylolz/WEF/pull/227."
    - "Owner Review with AI console on /admin/places with generate/apply POST flows, escaped diffs, and admin HTTP tests."
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# E19-T2: Owner AI place-review console and production controls

## Outcome

`/admin/places` exposes an owner-only **Review with AI** flow that clearly shows
source coverage, current-versus-proposed values, confidence/warnings, and a
separate explicit apply action with safe failure, stale, and rollback behavior.

## Scope

- Add the per-place action and owner-only generate/review/apply routes under the
  existing Starlette Admin mount.
- Render source selected/omitted counts, overall verdict, field diffs, confidence,
  evidence references, warnings, and provider/configuration failures.
- Require the owner to select each field; default to no selected changes and show
  that coordinate verification remains a separate E18 action.
- Handle loading/double-submit, refusal, timeout, expired/stale review, collision,
  no-change, conflicting evidence, and insufficient evidence accessibly.
- Add HTTP/security/browser tests and production configuration, smoke, monitoring,
  disable/rollback, and Groq Zero Data Retention/free-limit documentation.

## Out of scope

- Backend review/apply behavior beyond E19-T1.
- Public/ordinary-user UI, conversational chat, bulk review, automatic apply,
  coordinate changes, or location merge.
- Making Groq health part of readiness.

## Affected modules and contracts

- `apps/backend/src/wef_backend/features/admin/interface/views.py`
- `apps/backend/src/wef_backend/features/admin/interface/mount.py`
- Admin HTTP and browser tests
- `AI/security/AUTH_ADMIN_CONTACTS.md`, `AI/operations/DEPLOYMENT.md`,
  `AI/architecture/SYSTEM.md`

## Implementation notes

- Reuse `OwnerAuthProvider`, CSRF forms, origin guard, request IDs, and admin audit
  conventions; do not expose an OpenAPI route or API key to the browser.
- Use ordinary server-rendered HTML and POST/303 flows. A browser refresh or
  duplicate form submission cannot generate or apply twice accidentally.
- Keep the existing manual map picker as the next step after a spatial field
  correction.
- The action is absent or clearly disabled when the feature is off or provider
  configuration is incomplete.

## Acceptance criteria

- [ ] Anonymous and non-owner users cannot see or reach any AI review route;
  missing/foreign CSRF and origin are rejected.
- [ ] The action is absent or clearly disabled when the feature is off or provider
  configuration is incomplete; the rest of `/admin/places` still works.
- [ ] Generate shows exact source coverage and never describes omitted descriptions
  as reviewed.
- [ ] The result distinguishes no-change, proposed correction, conflict,
  insufficient evidence, provider failure, expired/stale, and collision states.
- [ ] Current/proposed values are safely escaped; no HTML/provider text executes,
  and no contact or raw source body appears in logs or generic error pages.
- [ ] No change is selected by default. Apply clearly identifies chosen fields and
  requires a separate owner POST; duplicate apply is idempotent.
- [ ] After address/district application, the UI says that the place is back in
  `needs_review` and links to E18's point verification flow.
- [ ] HTTP and browser tests cover authorization, CSRF/origin, accessibility,
  prompt-like output escaping, happy/no-change/failure/stale/collision paths, and
  feature-disabled behavior.
- [ ] Operations docs cover secret/config ownership, Zero Data Retention
  verification, free-limit monitoring, activation smoke, feature-flag disable,
  and rollback.
- [ ] `make lint`, `make format-check`, `make typecheck`, `make test`, and
  `make contract-check` pass; no public OpenAPI change is produced.

## Test plan

- Unit: none beyond T1 interactors.
- Integration: admin HTTP against fake services.
- Contract/migration: none.
- End-to-end: Playwright or existing admin browser harness for generate/apply
  and disabled states.
- Security/accessibility/operations: CSRF/origin, owner gate, escaped output,
  feature-disabled `/admin/places`.

## Rollout and rollback

Depends on merged E19-T1. Rollback is the prior image plus the disabled flag.
Do not enable production Groq from this task.

## Ready checklist

- [x] The file is authoritative under `tasks/`; no duplicate remains under `proposed-tasks/`.
- [x] Promotion source, promoter, and timestamp are recorded.
- [x] `spike_gate` references the owner-approved current spike revision and is `satisfied`.
- [x] `implementation_gate` references the owner-approved current implementation-plan revision, which contains this task ID/current revision, and is `satisfied`.
- [x] Every dependency is `done` with `dependency_gate: satisfied`, or each incomplete dependency is an ancestor PR recorded by `dependency_gate: stacked`.
- [x] Scope and acceptance criteria match the approved plan.

## Start checklist

- [x] Status passed through `ready`.
- [x] One new branch contains this task ID.
- [x] The branch and pull request contain this task only.
- [x] `branch.name` and `branch.created_at` are recorded before setting `in_progress`.

## Done checklist

- [ ] Acceptance criteria pass.
- [ ] The global [definition of done](../../../workflow/DEFINITION_OF_DONE.md) passes.
- [ ] Completion actor, time, pull request, and evidence are recorded.
