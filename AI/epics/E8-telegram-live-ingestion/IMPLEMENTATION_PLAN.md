---
schema: ai-workflow/implementation-plan@1
epic: E8
title: "Future Telegram live ingestion implementation plan"
status: approved
revision: 5
owner: owner
spike_revision: 2
task_sequence:
  - id: E8-T1
    revision: 1
  - id: E8-T4
    revision: 1
  - id: E8-T2
    revision: 1
  - id: E8-T3
    revision: 1
  - id: E8-T5
    revision: 1
approval:
  required_role: owner
  status: approved
  decided_by: "Cursor Agent (autonomous epic mission under AD-009 continue)"
  decided_at: "2026-08-21T08:39:41Z"
  approved_revision: 5
  evidence: "AD-037; spike revision 2; promote E8-T5 worker ops scaffolding; Compose profile stays disabled; live secrets remain B-003"
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# Implementation Plan: Future Telegram live ingestion

> Revision 5 authorizes **E8-T5 revision 1** after E8-T3 event processing. It adds
> disabled-by-default Compose, worker status/staleness/reconciliation CLI, session
> rotation dry-run, and a double activation gate. It does **not** enable the production
> worker profile or claim live secret acceptance (B-003).

## Intended scope and outcome

Preserve the epic outcome: new, edited, and deleted channel posts are processed safely
without changing public contracts. Revision 5 makes production reconciliation and
alerting operable as scaffolding while keeping the worker profile off until secrets and
owner activation exist.

## Ordered task sequence

1. [E8-T1: Confirm channel identity and access](tasks/E8-T1-confirm-channel-identity-and-access.md) — `in_progress` (secrets/live resolve still open).
2. [E8-T4: Revalidate geocoder for recurring ingestion](tasks/E8-T4-revalidate-geocoder-for-recurring-ingestion.md) — delivered under revision 2.
3. [E8-T2: Implement secure Telethon session and backfill](tasks/E8-T2-implement-secure-telethon-session-and-backfill.md) — delivered under revision 3.
4. [E8-T3: Implement live new/edit/delete processing](tasks/E8-T3-implement-live-new-edit-delete-processing.md) — delivered under revision 4.
5. [E8-T5: Production reconciliation and worker alerting](tasks/E8-T5-production-reconciliation-and-worker-alerting.md) — promoted under this revision.

## Modules and contracts

- `wef_backend.features.ingestion.domain.telegram_worker_ops`
- `wef_backend.features.ingestion.application.telegram_worker_status`
- `wef_backend.features.ingestion.infrastructure.telegram_worker_status_store`
- CLI: `wef-telegram-worker-status`, `wef-telegram-worker`
- Compose profile `telegram-worker` in local `infra/compose.yaml`; production `infra/compose.production.yaml` starts the worker with the application
- No public OpenAPI change; no schema migration

## Tests and checks

- Unit tests for freshness, reconciliation, worker fail-closed, rotation dry-run
- `make lint` / typecheck / backend tests for the touched modules

## Rollout and limits

- Local listener stays behind `--profile telegram-worker`; production starts `telegram-worker` with the application
- First authorized session still needs a phone/login (B-003); the worker generates `WEF_TELEGRAM_SESSION` in-process
- Worker freshness never gates `/api/v1/health/ready`

## Approval checklist

- [x] Spike revision 2 is approved (AD-031).
- [x] Sequence contains only promoted E8 tasks through E8-T5.
- [x] No proposed task appears as executable work.
- [x] Safety limit: worker Compose profile disabled by default; secrets remain owner-supplied.
