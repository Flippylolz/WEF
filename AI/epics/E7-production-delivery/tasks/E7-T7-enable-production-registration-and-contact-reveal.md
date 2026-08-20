---
schema: ai-workflow/task@1
id: E7-T7
epic: E7
title: "Enable production registration and contact reveal"
status: done
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
  pull_request: "https://github.com/Flippylolz/WEF/pull/123"
completion:
  completed_by: "Cursor Agent (autonomous epic mission)"
  completed_at: "2026-08-20T15:30:24Z"
  pull_request: "https://github.com/Flippylolz/WEF/pull/123"
  evidence:
    - "Enablement: merged https://github.com/Flippylolz/WEF/pull/123 (contact keys + proxy trust + owner bootstrap)"
    - "Admin edge route: merged https://github.com/Flippylolz/WEF/pull/124; live Nginx /admin → API"
    - "Reveal missing-offer 404: merged https://github.com/Flippylolz/WEF/pull/125"
    - "Deploy runs: 32383014398, 32384778680, 32385169695 succeeded; owner bootstrap once; bootstrap GitHub secrets removed"
    - "HTTPS smoke: register/login Secure cookies; owner password change; /admin/users; reveal unknown offer → 404"
    - "Plain :3100 /api/v1/auth/me → 401 (Secure cookies do not stick); Forecast :3000 → 200"
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
- Shared-edge `/admin` routing (`infra/nginx/tls*.conf.in`, Caddyfiles)
- Operations/security docs and B-002

## Acceptance criteria

- [x] Secure public/admin cookies work on the public HTTPS origin.
- [x] Username registration/login/password change and forced owner reset work on HTTPS.
- [x] Owner console `/admin` works after one-time bootstrap.
- [x] Plain HTTP (`:3100`) cannot establish/reuse a production Secure auth/admin session or reveal contacts.
- [x] Reveal/admin audits contain required account/action metadata without contact/IP/user-agent/password/token data.
- [x] Anonymous browsing remains available if authentication/admin is degraded.
- [x] No bootstrap passwords or contact keys are committed.

## Rollback

Redeploy previous release config without contact keys / without bootstrap; leave shared edge and Forecast unchanged.
