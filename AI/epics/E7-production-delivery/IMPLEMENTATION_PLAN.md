---
schema: ai-workflow/implementation-plan@1
epic: E7
title: "Enable production registration, sessions, admin, and contact reveal on HTTPS"
status: approved
revision: 8
owner: owner
spike_revision: 4
task_sequence:
  - id: E7-T7
    revision: 3
approval:
  required_role: owner
  status: approved
  decided_by: Flippylolz
  decided_at: "2026-08-20T14:43:16Z"
  approved_revision: 8
  evidence: "Owner continue after E7-T10 live HTTPS; AD-009 bounded plan revision; ADR-019 HTTPS gate satisfied"
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# Implementation Plan: Enable sensitive WEF features on HTTPS (revision 8)

> Revision 8 authorizes only E7-T7 revision 3 after completed E7-T10.

## Approved spike baseline

- [Spike revision 4](SPIKE.md) remains current.
- [ADR-019](../../decisions/adr/ADR-019-anonymous-http-production-rehearsal.md) requires E7-T10 HTTPS before E7-T7 sensitive enablement; E7-T10 is `done`.
- E6-T4, E6-T5, E6-T6, E6-T7, and E7-T4 are `done`.

## Scope and outcome

Enable production registration, sessions, owner administration, and contact reveal on `https://2fa54e2405.duckdns.org` with contact crypto keys, one-time owner bootstrap, and trusted proxy headers behind the shared Nginx edge.

## Ordered task sequence

### 1. E7-T7 (revision 3) — Enable production registration and contact reveal

- Task: [E7-T7](tasks/E7-T7-enable-production-registration-and-contact-reveal.md).
- Wire contact encryption/HMAC secrets and optional owner bootstrap into deploy configuration.
- Trust forwarded HTTPS headers so Secure cookies and same-origin CSRF match the public origin.
- Bootstrap the fixed owner once; rotate/remove bootstrap password after success.
- Prove HTTPS auth/admin/reveal smokes; keep anonymous browsing; leave Forecast `:3000` and Caddy `:3100` as rollback.

## Security and operations

- Clear B-002 only after live evidence.
- Do not activate historical public data (E7-T11).

## Invalidation triggers

Return to the spike if auth/cookie/CSRF model changes or HTTPS is withdrawn.

## Owner decision

Flippylolz authorized continuation after E7-T10 (chat continue 2026-08-20). Revision 8 sequences E7-T7 revision 3 only.
