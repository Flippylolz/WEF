---
schema: ai-workflow/task@1
id: E6-T7
epic: E6
title: "Implement owner administration console"
status: ready
revision: 1
priority: P1
size: L
milestone: M3
dependencies: [E6-T4, E6-T5]
requirement_ids: [P-008]
decision_ids: [ADR-011, ADR-012, ADR-016]
deferred_decision_ids: []
promotion:
  source: ../proposed-tasks/E6-T7-implement-owner-administration-console.md
  promoted_by: "Cursor Agent (autonomous epic mission)"
  promoted_at: "2026-08-20T11:51:18Z"
spike_gate:
  status: satisfied
  file: ../SPIKE.md
  approved_revision: 2
  verified_by: "Cursor Agent (autonomous epic mission)"
  verified_at: "2026-08-20T11:51:18Z"
implementation_gate:
  status: satisfied
  file: ../IMPLEMENTATION_PLAN.md
  approved_revision: 5
  verified_by: "Cursor Agent (autonomous epic mission)"
  verified_at: "2026-08-20T11:51:18Z"
dependency_gate:
  status: satisfied
  verified_by: "Cursor Agent (autonomous epic mission)"
  verified_at: "2026-08-20T11:51:18Z"
  evidence:
    - "E6-T4 | done | identity sessions (PR #51)"
    - "E6-T5 | done | contact reveal API and audit persistence (PR #110)"
branch:
  required: true
  name: feat/E6-T7-owner-admin-console
  task_id: E6-T7
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

# E6-T7: Implement owner administration console

## Outcome

Starlette Admin at `/admin` provides the owner-only console so authorized operators can manage accounts/sessions, force temporary password resets, and inspect minimized reveal/admin audits through application interactors—without exposing hashes, tokens, or contacts.

## Scope

- Integrate Starlette Admin at `/admin` with a custom owner `AuthProvider` backed by the existing identity session stack.
- Wire one-time owner bootstrap (already present) plus owner-authorized interactors for disable/reactivate, session revocation, forced temporary-password reset, reveal-audit queries, and admin auditing.
- Enforce CSRF/origin, rate limits, `Cache-Control: no-store`, last-owner protection, and sensitive-field restrictions on admin views/actions.
- Cover authorization, CSRF/origin, IDOR, and sensitive-field negative tests.

## Out of scope

- Production HTTPS enablement of registration/admin/reveal (E7-T7).
- Generic CRUD over users/sessions/contacts models.
- Next.js duplication of admin CRUD or business logic.
- E6-T1/T2/T3 pyramid/hardening/diagnostics work.

## Affected modules and contracts

- Backend: Starlette Admin mount, owner auth provider, admin views/actions, identity/admin interactors and persistence (including `AdminAuditEvent` if not already complete), settings for admin cookie/CSRF as needed.
- Dependencies: add `starlette-admin` only as already selected by the approved spike / AUTH_ADMIN_CONTACTS (no alternate admin framework).
- OpenAPI: admin is not part of the public contract; do not expose `/admin` in committed OpenAPI.

## Acceptance criteria

- [ ] No owner credential is hardcoded; bootstrap remains one-time/idempotent and its operator secret is rotated after success.
- [ ] Non-owner users cannot access any admin route/action.
- [ ] Generic admin forms never expose or write password hashes, session tokens, encrypted/plain contacts, or secrets.
- [ ] Every owner mutation uses an application interactor and writes a redacted `AdminAuditEvent`.
- [ ] CSRF/origin, rate-limit, no-store, and last-owner protections are covered by tests.

## Rollback

Redeploy previous backend image; drop or ignore unused admin audit rows if a migration was added. No frontend rollback required.
