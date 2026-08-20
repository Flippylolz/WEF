---
schema: ai-workflow/implementation-plan@1
epic: E6
title: "Privacy and security hardening after public HTTPS launch"
status: proposed
revision: 6
owner: owner
spike_revision: 2
task_sequence:
  - id: E6-T2
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

# Proposed Implementation Plan revision 6: Privacy and security hardening

> **Awaiting approval.** Follows completed E7-T10/E7-T7/E7-T11 public HTTPS, auth, and historical activation.

## Why this revision

- E6-T4/T5/T6/T7 are `done`; E3-T4, E4-T3, and E5-T3 dependencies for E6-T2 are `done`.
- Public historical data and sensitive features are live; DEPLOYMENT.md still defers HSTS until after verified certs (now satisfied).
- Remaining M3 E6 candidates: E6-T2 (this revision), then E6-T3/E6-T1 in later revisions.

## Scope and outcome

Promote and execute **E6-T2 revision 1**: close residual privacy/security gaps for the live HTTPS origin — enable HSTS on the shared edge, prove docs/OpenAPI stay 404, confirm contact/media/secret boundaries, refresh misleading synthetic-only public copy, and record audit/scan evidence.

## Ordered task sequence

### 1. E6-T2 (revision 1) — Perform privacy and security hardening

- Add `Strict-Transport-Security` to WEF HTTPS Nginx templates after E7-T10 cert verification.
- Regression-test docs/OpenAPI 404s, security headers, media dotfile denial, and anonymous contact non-disclosure.
- Review public copy/source-text presentation for post-activation honesty (no false “synthetic-only” claim).
- Confirm CI `pip-audit` / `pnpm audit --prod` remain clean or explicitly accept findings.
- Live-apply shared-edge HSTS on NUC and smoke HTTPS headers without changing Forecast `:3000` or Caddy `:3100`.

## Out of scope

- E6-T1 Playwright pyramid, E6-T3 diagnostics, E7-T5 backups, E8 Telegram, bulk `needs_review`→`visible` promotion.

## Owner decision required

1. Approve **this revision 6** under AD-009 continue authority after E7-T11.
