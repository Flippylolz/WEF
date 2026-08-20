---
schema: ai-workflow/implementation-plan@1
epic: E7
title: "Enable production registration, sessions, admin, and contact reveal on HTTPS"
status: proposed
revision: 8
owner: owner
spike_revision: 4
task_sequence:
  - id: E7-T7
    revision: 3
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

# Proposed Implementation Plan revision 8: Enable sensitive WEF features on HTTPS

> **Awaiting approval.** Follows completed E7-T10 live WEF HTTPS on `2fa54e2405.duckdns.org`.

## Why this revision

- E7-T10 is `done` (PR #121 + live cutover 2026-08-20). ADR-019’s HTTPS gate is satisfied for WEF.
- E6-T4–T7 identity/contacts/admin are implemented but production still lacks contact crypto keys, owner bootstrap, and trusted proxy headers required for Secure cookies and same-origin CSRF behind Nginx.
- B-002 remains until this enablement.

## Scope and outcome

Promote and execute **E7-T7 revision 3**: wire production secrets for contact encryption and one-time owner bootstrap, trust `X-Forwarded-Proto`/`Host` from the shared edge, deploy, bootstrap the owner once, and prove registration/login/admin/reveal paths on `https://2fa54e2405.duckdns.org` while plain `:3100` cannot establish Secure auth cookies.

## Ordered task sequence

### 1. E7-T7 (revision 3) — Enable production registration and contact reveal

- Require `WEF_CONTACT_ENCRYPTION_KEY` and `WEF_CONTACT_HMAC_KEY` in release config/deploy.
- Optionally pass `WEF_BOOTSTRAP_OWNER_USERNAME` / `WEF_BOOTSTRAP_OWNER_PASSWORD` for one-time owner creation; remove/rotate after success.
- Configure Uvicorn/API to honor forwarded HTTPS headers from Nginx.
- Smoke: register/login on HTTPS origin; admin `/admin` reachable with Secure cookies; reveal fails closed without keys only in pre-enable tests; Forecast `:3000` unchanged.
- Clear B-002 when evidence is recorded.

## Security and operations

- No certs/keys/bootstrap passwords in Git.
- Do not remove Caddy `:3100` or Forecast `:3000` in this task.
- E7-T11 historical public activation remains separate.

## Owner decision required

1. Approve **this revision 8** (or amend) under AD-009 continue authority after E7-T10.
