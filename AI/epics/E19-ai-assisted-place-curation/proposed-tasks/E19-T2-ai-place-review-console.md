---
schema: ai-workflow/proposed-task@1
id: E19-T2
epic: E19
title: "Owner AI place-review console and production controls"
status: proposed
revision: 2
actionable: false
priority: P1
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
source: "Owner request on 2026-08-30 for a Groq GPT-OSS place update/validation button based on raw descriptions"
promotion:
  status: not_promoted
  target: null
  promoted_by: null
  promoted_at: null
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

## Work

- Reuse `OwnerAuthProvider`, CSRF forms, origin guard, request IDs, and admin audit
  conventions; do not expose an OpenAPI route or API key to the browser.
- Use ordinary server-rendered HTML and POST/303 flows. A browser refresh or
  duplicate form submission cannot generate or apply twice accidentally.
- Keep the existing manual map picker as the next step after a spatial field
  correction.

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

## Dependencies and gates

- E19-T1 must be `done`; it owns all provider, validation, persistence, and
  mutation behavior.
- Requires the approved E19 spike and implementation plan plus normal branch/CI
  gates. Production enablement is a separate explicit owner action after checking
  Zero Data Retention in the live Groq project and checking its free-plan limits.
  Paid usage requires a separate owner decision.

## Risks and notes

The main UI risk is making an AI suggestion look authoritative or making Apply
feel automatic. The page must call it a proposal, show uncertainty/source coverage,
select nothing by default, and keep the manual point-verification next step visible.

## Promotion checklist

- [ ] The epic spike is explicitly owner-approved for its current revision.
- [ ] Scope, acceptance, dependencies, priority, size, and traceability match the approved spike.
- [ ] Required deferred decisions are resolved.
- [ ] The file will be moved—not copied—to the epic's `tasks/`.
- [ ] Promotion metadata will identify the target, promoter, and timestamp.
