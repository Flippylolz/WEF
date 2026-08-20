---
schema: ai-workflow/implementation-plan@1
epic: E6
title: "Quality, security, and operations implementation plan"
status: approved
revision: 5
owner: owner
spike_revision: 2
task_sequence:
  - id: E6-T7
    revision: 1
approval:
  required_role: owner
  status: approved
  decided_by: Flippylolz
  decided_at: "2026-08-20T11:51:18Z"
  approved_revision: 5
  evidence: "Owner continue / autonomous epic mission (AD-009); E6-T4/E6-T5 done on main; E6-T6 done; AUTH_ADMIN_CONTACTS + spike already select Starlette Admin for E6-T7"
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# Implementation Plan: E6-T7 owner administration console

## Approved spike baseline

- [Spike revision 2](SPIKE.md) remains owner-approved.
- Binding docs: [AUTH_ADMIN_CONTACTS](../../security/AUTH_ADMIN_CONTACTS.md), ADR-011/012/016.
- Identity sessions (E6-T4) and contact reveal/audit persistence (E6-T5) are on `main`; this plan sequences only the owner console.

## Scope and outcome

Deliver the Starlette Admin owner console at `/admin` with custom owner auth, audited interactors for account/session/password-reset and reveal-audit inspection, and hardening (CSRF/origin, rate limits, no-store, last-owner, sensitive-field bans). No production HTTPS enablement (E7-T7).

## Ordered task sequence

1. [E6-T7: Implement owner administration console](tasks/E6-T7-implement-owner-administration-console.md) — revision 1.
   - Independently reviewable: backend-only admin mount + interactors/tests; public OpenAPI unchanged.
   - Dependencies: E6-T4, E6-T5 — both `done`.
   - Affected modules: Starlette Admin integration, identity/admin application layer, migrations if `AdminAuditEvent` storage is incomplete, pytest coverage.
   - Tests: non-owner denied; CSRF/origin failures; last-owner protection; forms never expose hashes/tokens/contacts; mutations write redacted audit events.
   - Out of scope: Next.js admin UI, E6-T1/T2/T3, production auth enablement (E7-T7).

Only E6-T7 is sequenced. Remaining proposed E6 tasks stay proposed until a later plan revision.

## Cross-task architecture

- Admin HTML is owned by Starlette Admin; Next.js does not duplicate CRUD.
- All mutations go through owner-authorized application interactors (never generic `ModelView` writes of sensitive fields).
- Session cookie flags and origin/CSRF checks align with the existing identity mutation middleware pattern.
- `/admin` stays off the public OpenAPI surface.

## Security and privacy

- Non-owners receive generic denial; no contact ciphertext/plaintext via admin forms or audit screens.
- Force-reset sets `must_change_password` and never logs temporary passwords.
- Admin responses use `Cache-Control: no-store`.
- Feature remains inert on plain HTTP until E7-T7 enables auth in production.

## Test and verification strategy

- Backend pytest for authz, CSRF/origin, IDOR, last-owner, and audit redaction.
- Existing backend lint/type/coverage CI gates; no frontend contract regen expected.

## Operations, rollout, and rollback

- Backend image redeploy; document one-time bootstrap secret rotation after first owner creation.
- Rollback: previous backend image; optional ignore of new audit rows.

## Risks and mitigations

- Admin frameworks tempting generic CRUD: explicitly ban sensitive model fields and require interactors.
- Dependency addition (`starlette-admin`): already selected by approved spike / AUTH_ADMIN_CONTACTS; pin via lockfile.
- Scope creep into E6-T1/T2/T3: keep out of this sequence.

## Invalidation triggers

- Material change to owner authorization or admin capability list in AUTH_ADMIN_CONTACTS.
- Requirement to put `/admin` on the public OpenAPI contract.
- Need to adopt a different admin framework than Starlette Admin.

## Approval checklist

- [x] Spike revision approved and valid.
- [x] Sequence entries are promoted tasks with acceptance criteria.
- [x] Dependencies complete.
- [x] Modules, tests, risks, rollback explicit.
- [x] No deferred decisions for this slice.
- [x] Approval under continue / AD-009.
