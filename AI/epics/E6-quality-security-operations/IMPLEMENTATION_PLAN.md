---
schema: ai-workflow/implementation-plan@1
epic: E6
title: "Quality, security, and operations implementation plan"
status: awaiting_approval
revision: 2
owner: owner
spike_revision: 2
task_sequence:
  - id: E6-T4
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

# Implementation Plan: E6-T4 in-house registration and sessions

## Approved spike baseline

- [Spike revision 2](SPIKE.md) is owner-approved (PR #49, squash cd2ad36) and current.
- Binding decisions: project-owned identity module with `pwdlib[argon2]` and opaque database sessions (FastAPI Users and email-first identity rejected); only E6-T4 is actionable in this cycle; E6-T1/T2/T3/T5/T6/T7 remain under `proposed-tasks/` unactionable until their E3/E4/E5 dependencies complete.

## Scope and outcome

Deliver the first E6 slice toward "production behavior is tested, privacy-aware, observable, and recoverable": pseudonymous username/password registration, login/logout, password change, session revocation, forced-password-change state, and owner bootstrap, with anonymous browsing untouched. E7-T7 later activates registration in production.

## Ordered task sequence

1. [E6-T4: Implement in-house registration and sessions](tasks/E6-T4-implement-in-house-registration-and-sessions.md) — revision 1.
   - Independently reviewable: one new `identity` feature, one additive migration, additive OpenAPI paths; no existing catalog contract changes.
   - Dependencies: E1-T2 (done), E3-T1 (done); dependency gate satisfied with evidence recorded in the task file.
   - Affected modules/contracts: `features/identity/`, `composition.py`, `app.py` middleware, new Alembic revision, `contracts/openapi/v1.json`, regenerated `apps/web/src/generated/api.ts`.
   - Tests: unit (hashing/tokens/state machine), integration (flows against disposable PostGIS), contract (deterministic export + codegen + oasdiff), security (redaction, anti-enumeration, CSRF/origin, rate limits).
   - Migration: additive `users`/`sessions`; `EXPECTED_DATABASE_REVISION` advances; rollback is redeploy-previous (additive tables remain unused).
   - Risks and mitigations are recorded in the task file and below.

Only E6-T4 is sequenced. No proposed task appears here; later E6 candidates are re-sequenced by a future material plan revision after their dependencies complete.

## Cross-task architecture

- The `identity` feature follows the same domain → application → interface/infrastructure direction as `catalog`/`ingestion`, enforced by import-linter; domain/application layers import no fastapi/sqlalchemy/pydantic.
- Authorization decisions live in application interactors; routes only transport. Session lookup is a composition-root-wired adapter, mirroring the existing `app.state` pattern.
- The task adds no domain rules that duplicate catalog logic; no frontend domain state is introduced (E6-T6 owns restricted-action UX).

## Data and migrations

- One new Alembic revision creating `users` (unique username, Argon2 hash, `role`, `status`, forced-change flag) and `sessions` (token hash, user reference, expiry, revocation).
- Opaque random tokens; only their hashes persist. Migration is additive and replay-safe; integration tests replay it from the current baseline.
- Rollback boundary: redeploy the previous image; readiness's `EXPECTED_DATABASE_REVISION` gate restores consistency. ADR-015 applies: no backup/recovery guarantee is claimed for persisted account rows.

## Security and privacy

- Argon2 via `pwdlib` with current recommended parameters; anti-enumeration on register/login; cookies HttpOnly/Secure/SameSite; origin/CSRF checks on state-changing routes; per-account/per-IP auth rate limits; one-time owner bootstrap from an Actions secret (ADR-014 ownership).
- Negative tests prove passwords, hashes, tokens, and cookies never appear in logs or public responses. No email/verification surface exists (ADR-016).
- No contact data is touched by this task (E6-T5 scope).

## Test and verification strategy

- Acceptance maps to the task's test plan: pytest unit suites, PostGIS integration flows, deterministic OpenAPI export diff, frontend codegen/lint/docs, oasdiff non-breaking proof, CI architecture/coverage/audit gates.
- CI remains the merge gate; no dedicated production verification is claimed by this task (E7-T7/T10 own activation and live verification).

## Operations, rollout, and rollback

- Deploy follows the existing Actions-owned migrate-then-serve flow; the readiness revision gate blocks serving before migration completes.
- Owner bootstrap is an explicit manual operator command; its secret stays in GitHub Actions secrets and is never logged.
- Rollback is image redeploy; no persistent NUC data is described as backed up (ADR-015 deferral).

## Risks and mitigations

- Session/cookie abuse without TLS: cookies are Secure; auth admin actions stay disabled on plain HTTP; production activation is E7-T7.
- Rate-limit state growth: bounded design with documented limits; PostgreSQL-backed counters or explicit in-memory bounds.
- Bootstrap secret leakage: one-time command, no-owner precondition, no logging of secret material, CI secret-exclusion assertions extended if needed.
- Scope creep toward E6-T5/T6/T7: explicitly out of scope in the task file.

## Invalidation triggers

- Completion or re-scope of E3/E4/E5 blocking dependencies that changes E6 sequencing.
- Any persisted/public contract change in the identity surface beyond this plan.
- A material security-model change (session model, cookie transport, owner bootstrap ownership).

## Approval checklist

- [x] The referenced spike revision has explicit owner approval and remains valid.
- [x] Every sequence entry is a promoted task with complete acceptance criteria and traceability.
- [x] Dependencies are complete, acyclic, and enforceable task by task.
- [x] Affected modules, contracts, tests, migrations, risks, rollout, and rollback are explicit.
- [x] Deferred decisions required for implementation are resolved.
- [x] No production or disposable proof code has been written.
- [x] `revision` represents the material plan being submitted.
- [x] `status` is `awaiting_approval` and approval remains `pending`.

## Owner decision

The owner records the decision only in the YAML `approval` object. Approval authorizes the recorded plan revision, not blanket epic implementation: each task must still satisfy promotion, dependency, state, and one-branch-per-task gates.
