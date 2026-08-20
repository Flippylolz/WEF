---
schema: ai-workflow/implementation-plan@1
epic: E7
title: "WEF-only shared TLS after D-009 (Forecast stays on :3000)"
status: awaiting_approval
revision: 7
owner: owner
spike_revision: 4
task_sequence:
  - id: E7-T10
    revision: 2
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

# Proposed Implementation Plan revision 7: WEF-only shared TLS

> **Awaiting approval.** Revises revision 6 after the owner resolved [D-009](../../decisions/deferred/D-009-shared-tls-hostnames-and-forwarding.md): TLS for WEF on `2fa54e2405.duckdns.org`; AI Forecast remains on public port **3000** only (no second hostname).

## Why this revision

- Owner decision (2026-08-20): keep `2fa54e2405.duckdns.org` for **WEF**; Forecast accessible via **:3000** only.
- Funbox already forwards public **80/443** to the NUC; `:3100`/`:3000` remain for rollback.
- Dual-hostname Forecast TLS from revision 6 / ADR-020 default is **deferred**, not executed in E7-T10 revision 2.

## Scope and outcome

Promote and execute **E7-T10 revision 2**: shared Nginx/Certbot edge terminates TLS for WEF only on `2fa54e2405.duckdns.org`, routes web/API/media to private WEF upstreams, issues/renews Let's Encrypt for that single name, and leaves AI Forecast's host listener on **:3000** unchanged.

## Ordered task sequence

### 1. E7-T10 (revision 2) — Roll out and verify WEF-only shared TLS

- Adapt shared-edge render/smoke/cutover proofs for optional Forecast hostname (WEF-only mode).
- Live NUC: inventory, HTTP-01 bootstrap, staging then production cert for `2fa54e2405.duckdns.org`, activate TLS, migrate WEF off public dependence on `:3100`, HTTP→HTTPS redirect for the WEF hostname only.
- Prove Forecast `http://…:3000` health before/after; do not move Forecast behind Nginx in this task.
- Dependencies: E7-T9 `done`; D-009 `resolved`.

## Security and operations

- Certificates/DuckDNS tokens stay off Git.
- Sensitive WEF features still wait for E7-T7 after HTTPS.
- Update B-009 when cutover completes; B-002 clears only after E7-T7.

## Owner decision required

1. Approve **this revision 7** (or amend).
2. Authorize live E7-T10 cutover on a dedicated branch/PR after tooling adaptation merges.
