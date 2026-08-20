---
schema: ai-workflow/implementation-plan@1
epic: E6
title: "Privacy and security hardening after public HTTPS launch"
status: approved
revision: 6
owner: owner
spike_revision: 2
task_sequence:
  - id: E6-T2
    revision: 1
approval:
  required_role: owner
  status: approved
  decided_by: Flippylolz
  decided_at: "2026-08-20T16:17:08Z"
  approved_revision: 6
  evidence: "Owner continue after E7-T11; AD-009 bounded plan revision; E6 spike revision 2; E6-T2 dependencies E3-T4/E4-T3/E5-T3 done"
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# Implementation Plan: Privacy and security hardening (revision 6)

> Revision 6 authorizes only E6-T2 revision 1 after public HTTPS, auth, and historical activation.

## Approved spike baseline

- [Spike revision 2](SPIKE.md) remains owner-approved.
- Binding docs: [AUTH_ADMIN_CONTACTS](../../security/AUTH_ADMIN_CONTACTS.md), [DEPLOYMENT](../../operations/DEPLOYMENT.md), ADR-007/011/013/016.
- E6-T4/T5/T6/T7 are `done`; E7-T10/T7/T11 are `done`.

## Scope and outcome

Close residual privacy/security gaps on the live HTTPS origin: HSTS, docs/OpenAPI denial proofs, contact/media/secret boundaries, public-copy honesty after historical activation, and dependency-scan evidence.

## Ordered task sequence

### 1. E6-T2 (revision 1) — Perform privacy and security hardening

- Task: [E6-T2](tasks/E6-T2-perform-privacy-and-security-hardening.md).
- Independently reviewable: shared-edge header templates + regression tests + public copy; no schema/auth redesign.
- Dependencies: E3-T4, E4-T3, E5-T3 — all `done`.
- Affected modules: `infra/nginx/tls*.conf.in`, shared-edge proofs, optional web `messages/en.json`, security/ops docs.
- Tests: topology/render proofs for HSTS; API docs 404; live HTTPS header smoke after NUC apply.
- Out of scope: E6-T1/T3, bulk visibility promotion, Forecast TLS, backups.

## Security and privacy

- HSTS only on HTTPS WEF vhost after verified Let's Encrypt (E7-T10); do not advertise HSTS on `:3100`.
- Preserve CSP/Referrer-Policy/X-Content-Type-Options/X-Frame-Options already on the edge.
- No secrets in evidence; scans stay in CI.

## Operations, rollout, and rollback

- Render/apply shared-edge release on NUC from updated templates; `nginx -t` then reload.
- Rollback: previous edge release without HSTS header; WEF app rollback independent.

## Invalidation triggers

Return to the spike if hardening requires a new auth model, contact plaintext in public responses, or exposing OpenAPI in production.

## Owner decision

Flippylolz authorized continuation after E7-T11 (chat continue 2026-08-20). Revision 6 sequences E6-T2 revision 1 only; executed via PRs #130/#131 and live HSTS apply on 2026-08-20.
