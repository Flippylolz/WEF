---
schema: ai-workflow/task@1
id: E7-T7
epic: E7
title: "Enable production registration and contact reveal"
status: in_progress
revision: 3
priority: P1
size: M
milestone: M3
dependencies: [E6-T4, E6-T5, E6-T6, E6-T7, E7-T4, E7-T10]
requirement_ids: [P-008]
decision_ids: [ADR-010, ADR-011, ADR-014, ADR-016, ADR-019, ADR-020]
deferred_decision_ids: []
promotion:
  source: ../proposed-tasks/E7-T7-enable-production-registration-and-contact-reveal.md
  promoted_by: "Cursor Agent (autonomous epic mission)"
  promoted_at: "2026-08-20T14:44:43Z"
spike_gate:
  status: satisfied
  file: ../SPIKE.md
  approved_revision: 4
  verified_by: "Cursor Agent (autonomous epic mission)"
  verified_at: "2026-08-20T14:44:43Z"
implementation_gate:
  status: satisfied
  file: ../IMPLEMENTATION_PLAN.md
  approved_revision: 8
  verified_by: "Cursor Agent (autonomous epic mission)"
  verified_at: "2026-08-20T14:44:43Z"
dependency_gate:
  status: satisfied
  verified_by: "Cursor Agent (autonomous epic mission)"
  verified_at: "2026-08-20T14:44:43Z"
  evidence:
    - "E6-T4 | done"
    - "E6-T5 | done"
    - "E6-T6 | done"
    - "E6-T7 | done | PR #116"
    - "E7-T4 | done"
    - "E7-T10 | done | PR #121 + live HTTPS 2026-08-20"
branch:
  required: true
  name: feat/E7-T7-enable-auth-on-https
  task_id: E7-T7
  one_task_only: true
  created_at: "2026-08-20T14:43:16Z"
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

# E7-T7: Enable production registration and contact reveal

## Outcome

Enable secure public registration/login/password change, owner administration at `/admin`, and authenticated contact reveal on the live HTTPS origin `https://2fa54e2405.duckdns.org`, with audited metadata and anonymous browsing retained if auth degrades.

## Scope

- Add production contact encryption/HMAC keys to deploy-built `production.env` and Compose.
- Trust Nginx `X-Forwarded-Proto` / `Host` so Secure cookies and same-origin CSRF match HTTPS.
- One-time owner bootstrap from GitHub secrets; remove/rotate bootstrap password after success.
- Prove HTTPS auth/admin/reveal smokes; prove plain `:3100` cannot establish Secure production sessions.
- Clear B-002 when evidence is recorded.

## Out of scope

- Historical public activation (E7-T11), Telegram ingestion, Forecast TLS, removing `:3100`/`:3000`.

## Affected modules

- `scripts/deploy/build_release_config.py`, `validate_release.py`, `.github/workflows/deploy-production.yml`
- `infra/compose.production.yaml`, `apps/backend` CLI/proxy trust, owner bootstrap command
- Operations/security docs and B-002

## Acceptance criteria

- [ ] Secure public/admin cookies work on the public HTTPS origin.
- [ ] Username registration/login/password change and forced owner reset work on HTTPS.
- [ ] Owner console `/admin` works after one-time bootstrap.
- [ ] Plain HTTP (`:3100`) cannot establish/reuse a production Secure auth/admin session or reveal contacts.
- [ ] Reveal/admin audits contain required account/action metadata without contact/IP/user-agent/password/token data.
- [ ] Anonymous browsing remains available if authentication/admin is degraded.
- [ ] No bootstrap passwords or contact keys are committed.

## Rollback

Redeploy previous release config without contact keys / without bootstrap; leave shared edge and Forecast unchanged.
