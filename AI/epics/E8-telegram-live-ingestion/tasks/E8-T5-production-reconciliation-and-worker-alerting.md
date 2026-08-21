---
schema: ai-workflow/task@1
id: E8-T5
epic: E8
title: "Production reconciliation and worker alerting"
status: in_progress
revision: 1
priority: P2
size: L
milestone: M4
dependencies: [E8-T3, E8-T4]
requirement_ids: [P-006, P-007]
decision_ids: [ADR-006, ADR-010, ADR-015]
deferred_decision_ids: []
blocker_ids: [B-003]
source: "legacy-roadmap:E8-T5"
promotion:
  status: promoted
  target: tasks/E8-T5-production-reconciliation-and-worker-alerting.md
  promoted_by: "Cursor Agent (autonomous epic mission under AD-009 continue)"
  promoted_at: "2026-08-21T08:39:41Z"
---

# E8-T5: Production reconciliation and worker alerting

## Outcome

Ship disabled-by-default local/production Compose for `telegram-worker`, redacted
worker health/staleness + export-checkpoint reconciliation, session-rotation dry-run,
and an explicit production activation gate—without enabling the worker while B-003
secrets are missing.

## Work

- [x] Disabled-by-default `telegram-worker` Compose profile (local + production).
- [x] Secret-path transfer contract (`/run/secrets/wef_telegram_*`, host `secrets/current`).
- [x] `wef-telegram-worker-status` for last received/committed timestamps and reconciliation.
- [x] Freshness classification that never gates public API readiness.
- [x] Session rotation rehearsal dry-run checklist.
- [x] `wef-telegram-worker` entrypoint fail-closed unless `WEF_TELEGRAM_WORKER_ACTIVATE=1`.
- [ ] Live production activation with owner-supplied secrets (blocked on B-003).
- [ ] Continuous live loop enablement (`WEF_TELEGRAM_WORKER_LIVE_LOOP=1`) after activation evidence.

## Acceptance

- [x] Compose profile is present and off by default; ordinary `make up` / production deploy does not start the worker.
- [x] Last live checkpoint / finished_at and max persisted external message id are observable via CLI.
- [x] Unexplained live-ahead checkpoints are classified and exit non-zero from status CLI.
- [x] Rotation rehearsal is printable without mutating secrets.
- [ ] No unexplained source-message gaps after live activation (blocked on B-003).
- [ ] Outage recovery without full re-import after live activation (blocked on B-003).

## Safety limits

- Do not set `WEF_TELEGRAM_WORKER_ACTIVATE=1` or enable the Compose profile in production until B-003 is cleared and owner activation is recorded.
- Continuous live loop remains gated even after a successful session probe.
- Worker freshness must not affect `/api/v1/health/ready`.

## Dependencies and traceability

- Task dependencies: [E8-T3](E8-T3-implement-live-new-edit-delete-processing.md), [E8-T4](E8-T4-revalidate-geocoder-for-recurring-ingestion.md)
- Milestone: [M4](../../../milestones/M4-live-telegram-updates.md).
- Traceability: [Product requirements](../../../product/EXPERIENCE.md), [Decision registry](../../../decisions/README.md), [Ingestion](../../../ingestion/README.md), [Operations](../../../operations/DEPLOYMENT.md), [Security](../../../security/README.md).
