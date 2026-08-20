---
schema: ai-workflow/implementation-plan@1
epic: E6
title: "Operational diagnostics for production operators"
status: proposed
revision: 7
owner: owner
spike_revision: 2
task_sequence:
  - id: E6-T3
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

# Proposed Implementation Plan revision 7: Operational diagnostics

> **Awaiting approval.** Follows completed E6-T2 privacy/security hardening.

## Why this revision

- E6-T2 is `done`; E3-T2 and E4-T4 dependencies for E6-T3 are `done`.
- Operators still lack a single non-sensitive view of release identity, last deploy failure, disk pressure, and last successful import.
- Spike revision 2 called out unconfigured structlog and missing request-access logging.

## Scope and outcome

Promote and execute **E6-T3 revision 1**: host operator diagnostics JSON (release, last failure, disk usage, last successful import aggregates), configure structlog JSON access logs with redaction proofs, and document the operator flow.

## Ordered task sequence

### 1. E6-T3 (revision 1) — Add operational diagnostics

- Add `scripts/deploy/operator_diagnostics.py` under the WEF root with redacted JSON output.
- Configure structlog + request access logging (method/path/status/duration/request_id/release) without secrets or source text.
- Document usage in operations docs; unit-test redaction and fixture diagnostics.

## Out of scope

- E6-T1 Playwright pyramid, Prometheus/OTel exporters, backups (E7-T5), Telegram (E8).

## Owner decision required

1. Approve **this revision 7** under AD-009 continue authority after E6-T2.
