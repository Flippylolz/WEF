---
schema: ai-workflow/task@1
id: E6-T3
epic: E6
title: "Add operational diagnostics"
status: done
revision: 1
priority: P1
size: M
milestone: M3
dependencies: [E3-T2, E4-T4]
requirement_ids: [P-007]
decision_ids: [ADR-008, ADR-010, ADR-014, ADR-015]
deferred_decision_ids: []
promotion:
  source: ../proposed-tasks/E6-T3-add-operational-diagnostics.md
  promoted_by: "Cursor Agent (autonomous epic mission)"
  promoted_at: "2026-08-20T16:34:05Z"
spike_gate:
  status: satisfied
  file: ../SPIKE.md
  approved_revision: 2
  verified_by: "Cursor Agent (autonomous epic mission)"
  verified_at: "2026-08-20T16:34:05Z"
implementation_gate:
  status: satisfied
  file: ../IMPLEMENTATION_PLAN.md
  approved_revision: 7
  verified_by: "Cursor Agent (autonomous epic mission)"
  verified_at: "2026-08-20T16:34:05Z"
dependency_gate:
  status: satisfied
  verified_by: "Cursor Agent (autonomous epic mission)"
  verified_at: "2026-08-20T16:34:05Z"
  evidence:
    - "E3-T2 | done | idempotent persistence"
    - "E4-T4 | done | API behavior/performance"
branch:
  required: true
  name: feat/E6-T3-operational-diagnostics
  task_id: E6-T3
  one_task_only: true
  created_at: "2026-08-20T16:34:05Z"
  pull_request: "https://github.com/Flippylolz/WEF/pull/133"
completion:
  completed_by: "Cursor Agent (autonomous epic mission)"
  completed_at: "2026-08-20T17:11:41Z"
  pull_request: "https://github.com/Flippylolz/WEF/pull/133"
  evidence:
    - "Merged https://github.com/Flippylolz/WEF/pull/133 (operator diagnostics + structlog access logs + WEF_RELEASE_SHA)"
    - "Post-activation deploys unblocked by https://github.com/Flippylolz/WEF/pull/134; production release 11dd20b… live with WEF_RELEASE_SHA on API"
    - "Live operator_diagnostics JSON: release 11dd20b…, last_failure health_verification, disk ~5.5% used, last_successful_import e3-complete-v2 checksum prefix 2399a88c7025 (no source content)"
    - "Live API access logs emit http_request with method/path/status/duration_ms/release_sha/request_id; redaction unit tests cover passwords/tokens/source keys"
    - "Shared-edge reconnect after deploy restored HTTPS /api/v1/health/live → 200"
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# E6-T3: Add operational diagnostics

## Outcome

An operator can identify the active release, last deploy failure stage/reason, disk usage on WEF roots, and last successful import aggregates without reading source content — supported by structured request access logs with redaction proofs.

## Scope

- Host operator diagnostics command emitting redacted JSON from `$WEF_ROOT` state and optional DB import-run query.
- Configure structlog JSON logging and request access logs (method/path/status/duration/request_id/release).
- Document the operator flow; prove redaction negatives in tests.

## Out of scope

- E6-T1 Playwright pyramid, Prometheus/OpenTelemetry exporters, log shipping SaaS, backups (E7-T5), Telegram live ingestion (E8).

## Work

- Implement `scripts/deploy/operator_diagnostics.py` and unit tests.
- Wire logging configuration at API startup; extend request middleware for access events.
- Update operations docs and CI unittest list.

## Acceptance criteria

- [x] An operator can identify release, failed stage/reason, disk usage, and last successful import without reading source content.
- [x] Structured logs carry request/release correlation without secrets, contacts, or source text.
- [x] Negative redaction tests cover passwords, tokens, and source payloads.

## Dependencies and gates

- Dependencies: E3-T2, E4-T4 (`done`).
- Implementation plan revision 7 authorizes this task.
- Milestone: [M3](../../../milestones/M3-public-dockerized-mvp.md).

## Risks and notes

- Host disk stats and DB queries must fail closed with explicit errors, never partial secret leakage.
- Do not mount restricted originals into the API for diagnostics.
- Post-E7-T11 media symlinks require the deploy-gate allowance from PR #134 for subsequent releases.

## Rollback

Revert to prior API image and remove/ignore the diagnostics script; state files remain untouched.
