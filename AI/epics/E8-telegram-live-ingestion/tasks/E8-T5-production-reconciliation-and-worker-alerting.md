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

Ship local (profile-gated) and production Compose for `telegram-worker`, redacted
worker health/staleness + export-checkpoint reconciliation, and session-rotation
dry-run. Production starts the worker with the application; first authorized session
still needs a phone/login (B-003).

## Work

- [x] Disabled-by-default local `telegram-worker` Compose profile; production worker starts with the application.
- [x] Env credentials (`WEF_TELEGRAM_API_ID` / `WEF_TELEGRAM_API_HASH` / optional session) plus generated string session persist under `secrets/telegram`.
- [x] `wef-telegram-worker-status` for last received/committed timestamps and reconciliation.
- [x] Freshness classification that never gates public API readiness.
- [x] Session rotation rehearsal dry-run checklist.
- [x] `wef-telegram-worker` runs the live listen loop after in-app session generation.
- [ ] First authorized production session (phone/code) and live new/edit/delete evidence.

## Acceptance

- [x] Local Compose profile is off by default; ordinary production deploys start `telegram-worker`.
- [x] Last live checkpoint / finished_at and max persisted external message id are observable via CLI.
- [x] Unexplained live-ahead checkpoints are classified and exit non-zero from status CLI.
- [x] Rotation rehearsal is printable without mutating secrets.
- [ ] No unexplained source-message gaps after live activation (blocked on B-003).
- [ ] Outage recovery without full re-import after live activation (blocked on B-003).

## Safety limits

- Production `telegram-worker` starts with the application; it fail-closes until API credentials exist and a string session can be generated or loaded.
- Worker freshness must not affect `/api/v1/health/ready`.

## Dependencies and traceability

- Task dependencies: [E8-T3](E8-T3-implement-live-new-edit-delete-processing.md), [E8-T4](E8-T4-revalidate-geocoder-for-recurring-ingestion.md)
- Milestone: [M4](../../../milestones/M4-live-telegram-updates.md).
- Traceability: [Product requirements](../../../product/EXPERIENCE.md), [Decision registry](../../../decisions/README.md), [Ingestion](../../../ingestion/README.md), [Operations](../../../operations/DEPLOYMENT.md), [Security](../../../security/README.md).
