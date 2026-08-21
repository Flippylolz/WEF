---
schema: ai-workflow/implementation-plan@1
epic: E8
title: "Future Telegram live ingestion implementation plan"
status: approved
revision: 3
owner: owner
spike_revision: 2
task_sequence:
  - id: E8-T1
    revision: 1
  - id: E8-T4
    revision: 1
  - id: E8-T2
    revision: 1
approval:
  required_role: owner
  status: approved
  decided_by: "Cursor Agent (autonomous epic mission under AD-009 continue)"
  decided_at: "2026-08-21T07:46:50Z"
  approved_revision: 3
  evidence: "AD-035; spike revision 2; promote E8-T2 Telethon/session/backfill; no worker Compose enablement; live secrets remain B-003"
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# Implementation Plan: Future Telegram live ingestion

> Revision 3 authorizes **E8-T2 revision 1** after E8-T1/E8-T4 scaffolding and E3-T2
> persistence. It adds the Telethon dependency and backfill path. It does **not** enable
> the production worker Compose profile or claim live secret acceptance (B-003).

## Intended scope and outcome

Preserve the epic outcome: new, edited, and deleted channel posts are processed safely
without changing public contracts. Revision 3 implements secure session loading, entity
verification, advisory lock reuse, and restartable/idempotent backfill through the shared
ingestion persistence port.

## Ordered task sequence

1. [E8-T1: Confirm channel identity and access](tasks/E8-T1-confirm-channel-identity-and-access.md) — `in_progress` (secrets/live resolve still open).
2. [E8-T4: Revalidate geocoder for recurring ingestion](tasks/E8-T4-revalidate-geocoder-for-recurring-ingestion.md) — delivered under revision 2.
3. [E8-T2: Implement secure Telethon session and backfill](tasks/E8-T2-implement-secure-telethon-session-and-backfill.md) — promoted under this revision.

Later revisions will sequence E8-T3 → E8-T5 per the approved spike.

## Modules and contracts

- `wef_backend.features.ingestion.domain.telegram_secrets`
- `wef_backend.features.ingestion.application.telegram_live`
- `wef_backend.features.ingestion.application.telegram_backfill`
- `wef_backend.features.ingestion.infrastructure.fake_telegram_client`
- `wef_backend.features.ingestion.infrastructure.telethon_client`
- `wef_backend.telegram_backfill_command` (`wef-telegram-backfill`)
- Reuses E3 `IngestionPersistencePort` / `RunMode.LIVE` / advisory `run_lock`
- No public OpenAPI change; no schema migration; no worker Compose enablement

## Tests and checks

- Unit tests for secret mode gating, entity mismatch, fake restartable/idempotent backfill
- `make lint` / typecheck / backend tests for the touched modules

## Rollout and limits

- No production worker enablement (E8-T5)
- Live Telethon runs require owner-supplied GitHub/NUC secrets (B-003)
- Operator may run `wef-telegram-backfill` only where worker secret files exist

## Approval checklist

- [x] Spike revision 2 is approved (AD-031).
- [x] Sequence contains only promoted E8-T1, E8-T4, and E8-T2.
- [x] No proposed task appears as executable work.
- [x] Safety limit: no worker Compose profile enablement; secrets remain owner-supplied.
