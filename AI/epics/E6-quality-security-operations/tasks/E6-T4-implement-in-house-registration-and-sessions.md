---
schema: ai-workflow/task@1
id: E6-T4
epic: E6
title: "Implement in-house registration and sessions"
status: in_progress
revision: 1
priority: P1
size: L
milestone: M3
dependencies: [E1-T2, E3-T1]
requirement_ids: [P-008]
decision_ids: [ADR-011, ADR-012, ADR-016]
deferred_decision_ids: []
promotion:
  source: ../proposed-tasks/E6-T4-implement-in-house-registration-and-sessions.md
  promoted_by: "ZCode Agent (owner-authorized)"
  promoted_at: "2026-08-14T11:46:36Z"
spike_gate:
  status: satisfied
  file: ../SPIKE.md
  approved_revision: 2
  verified_by: "ZCode Agent"
  verified_at: "2026-08-14T11:46:36Z"
implementation_gate:
  status: satisfied
  file: ../IMPLEMENTATION_PLAN.md
  approved_revision: 2
  verified_by: "ZCode Agent"
  verified_at: "2026-08-14T21:30:59Z"
dependency_gate:
  status: satisfied
  verified_by: "ZCode Agent"
  verified_at: "2026-08-14T11:46:36Z"
  evidence:
    - "E1-T2 | done | task record ../../E1-repository-developer-foundation/tasks/E1-T2-scaffold-web-and-backend-applications.md | scaffolds live on integrated main cd2ad36"
    - "E3-T1 | done | task record ../../E3-database-geocoding-media/tasks/E3-T1-create-schema-and-migrations.md | schema/migrations live on integrated main cd2ad36"
branch:
  required: true
  name: feature/E6-T4-registration-sessions
  task_id: E6-T4
  one_task_only: true
  created_at: "2026-08-14T21:30:59Z"
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

# E6-T4: Implement in-house registration and sessions

## Outcome

Pseudonymous username/password accounts with opaque database-backed sessions exist behind the same modular-monolith contracts as the catalog, while anonymous browsing remains unchanged.

## Scope

- New `identity` feature (domain value objects + application interactors + interface transport + SQLAlchemy infrastructure) following the import-linter layer contracts.
- `users` and `sessions` schema in one dedicated Alembic migration: username uniqueness/collation, Argon2 password hash (`pwdlib[argon2]`), `role: user|owner`, `status`/forced-password-change state, opaque session tokens (store hash of token only), and expiry/revocation fields.
- Public auth endpoints under `/api/v1`: register, login, logout, password change, and session revocation; anti-enumeration responses; OpenAPI additions through the committed deterministic export.
- Opaque server-side sessions delivered as HttpOnly/Secure/SameSite cookies; origin/CSRF checks on state-changing routes; per-account and per-IP auth rate limits backed by PostgreSQL or explicitly bounded in-memory state.
- One-time owner bootstrap command fed from an Actions secret (succeeds only when no owner exists).
- Integration/security tests for every flow plus negative tests proving tokens, passwords, hashes, and cookies never appear in logs or public responses.

## Out of scope

- Contact reveal/masking/audit (E6-T5), restricted-action frontend UX and i18n routing (E6-T6), owner console (E6-T7), password reset without owner (no email exists by design).
- Production activation of registration (E7-T7 owns rollout); this task may keep feature activation configuration-neutral.

## Affected modules and contracts

- `apps/backend/src/wef_backend/features/identity/` (new), `composition.py` wiring, `app.py` middleware (origin/CSRF, rate limiting), `migrations/versions/` (new revision), `contracts/openapi/v1.json`, `apps/web/src/generated/api.ts` regeneration, [AUTH_ADMIN_CONTACTS](../../../security/AUTH_ADMIN_CONTACTS.md).

## Implementation notes

- Project-owned identity code per spike revision 2: E0's locked proof omitted FastAPI Users, and the username-only scope triggers the AUTH_ADMIN_CONTACTS escape clause. FastAPI Users is not added as a dependency.
- Domain/application layers must not import fastapi/sqlalchemy/pydantic (import-linter); authorization stays in interactors.
- Registration/login responses are generic on unknown username vs wrong password.
- Sessions are opaque random tokens; only a hash of the token is persisted; logout revokes server-side.
- `EXPECTED_DATABASE_REVISION` advances to the new migration revision so readiness gates the rollout.

## Acceptance criteria

- [ ] Anonymous browsing endpoints and their contracts remain unchanged.
- [ ] Registration/login/logout/password-change/revocation/account-disable/delete flows pass integration/security tests.
- [ ] Raw tokens, passwords, hashes, and session cookies do not appear in logs/public responses (negative tests).
- [ ] No email, verification, or self-service forgotten-password dependency exists.
- [ ] Public contact reveal remains disabled over non-HTTPS production configuration.
- [ ] Rate limits and origin/CSRF checks reject abusive/misoriginated state-changing requests in tests.
- [ ] Owner bootstrap succeeds only when no owner exists and records no secret material in logs.

## Test plan

- Unit: password hashing/verification, session token generation/hashing, forced-change state machine, rate-limit counters.
- Integration: auth flows against disposable PostGIS including migration replay; cookie attributes; CSRF/origin rejection.
- Contract: deterministic OpenAPI export updated; frontend codegen + oasdiff non-breaking checks.
- Security: log/response redaction probes, anti-enumeration equivalence, session revocation.

## Rollout and rollback

- Migration is additive (`users`/`sessions`); rollout order is migrate-then-serve via the existing readiness revision gate. Rollback: redeploy previous image; the additive tables remain but are unused. No data recovery beyond what ADR-015 defers.

## Ready checklist

- [x] The file is authoritative under `tasks/`; no duplicate remains under `proposed-tasks/`.
- [x] Promotion source, promoter, and timestamp are recorded.
- [x] `spike_gate` references the owner-approved current spike revision and is `satisfied`.
- [x] `implementation_gate` references the owner-approved current implementation-plan revision, which contains this task ID/current revision, and is `satisfied`.
- [x] Every dependency is `done` with `dependency_gate: satisfied`; no deferred gates apply.
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
