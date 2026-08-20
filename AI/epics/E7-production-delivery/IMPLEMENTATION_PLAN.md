---
schema: ai-workflow/implementation-plan@1
epic: E7
title: "WEF-only shared TLS after D-009 (Forecast stays on :3000)"
status: approved
revision: 7
owner: owner
spike_revision: 4
task_sequence:
  - id: E7-T10
    revision: 2
approval:
  required_role: owner
  status: approved
  decided_by: Flippylolz
  decided_at: "2026-08-20T13:45:55Z"
  approved_revision: 7
  evidence: "Owner continue after D-009 WEF-only resolution (PR #119); hostname 2fa54e2405.duckdns.org for WEF; Forecast remains on :3000; AD-022"
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# Implementation Plan: WEF-only shared TLS (revision 7)

> Revision 7 authorizes only E7-T10 revision 2. Forecast dual-hostname TLS from earlier drafts is deferred.

## Approved spike baseline

- [Spike revision 4](SPIKE.md) remains current.
- [D-009](../../decisions/deferred/D-009-shared-tls-hostnames-and-forwarding.md) is `resolved` (WEF hostname `2fa54e2405.duckdns.org`; Forecast stays on public `:3000`).
- [ADR-020](../../decisions/adr/ADR-020-use-nginx-shared-tls-ingress.md) owner amendment (2026-08-20) narrows the initial cutover to WEF-only shared TLS.
- E7-T1–T4, E7-T6, E7-T8, and E7-T9 are `done`.

## Scope and outcome

Deliver live shared Nginx/Certbot TLS for **WEF only** on `2fa54e2405.duckdns.org`, with ACME HTTP-01, renewal, WEF smokes through 443, HTTP→HTTPS redirect for that hostname, and AI Forecast left on host `:3000` unchanged.

## Ordered task sequence

### 1. E7-T10 (revision 2) — Roll out and verify WEF-only shared TLS

- Task: [E7-T10](tasks/E7-T10-roll-out-and-verify-shared-tls.md).
- Adapt shared-edge render/smoke/cutover/proofs for optional Forecast hostname; production path omits Forecast vhost.
- Live NUC: inventory, bootstrap ACME, staging then production cert, activate TLS, migrate WEF off sole dependence on `:3100`, WEF-only redirect; prove Forecast `:3000` health before/after.
- Dependencies: E7-T9 `done`; D-009 `resolved`.

## Security and operations

- Certificates and DuckDNS tokens stay off Git.
- Sensitive WEF features wait for E7-T7 after verified HTTPS.
- Clear B-009 when cutover completes; B-002 clears only after E7-T7.

## Invalidation triggers

Return to the spike for a different TLS terminator or restoring mandatory Forecast dual-hostname TLS in the same cutover. Return to this plan if WEF hostname or 80/443 forwarding assumptions change.

## Owner decision

Flippylolz authorized continuation after resolving D-009 as WEF-only TLS (chat 2026-08-20 + continue). Revision 7 sequences E7-T10 revision 2 only.
