---
schema: ai-workflow/implementation-plan@1
epic: E8
title: "Future Telegram live ingestion implementation plan"
status: approved
revision: 4
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
approval:
  required_role: owner
  status: approved
  decided_by: "Cursor Agent (autonomous epic mission under AD-009 continue)"
  decided_at: "2026-08-21T08:15:35Z"
  approved_revision: 4
  evidence: "AD-036; spike revision 2; promote E8-T3 live new/edit/delete; no worker Compose enablement; live secrets remain B-003"
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# Implementation Plan: Future Telegram live ingestion

> Revision 4 authorizes **E8-T3 revision 1** after E8-T2 backfill scaffolding. It adds
> serialized new/edit/delete processing through shared persistence. It does **not**
> enable the production worker Compose profile or claim live secret acceptance (B-003).

## Intended scope and outcome

Preserve the epic outcome: new, edited, and deleted channel posts are processed safely
without changing public contracts. Revision 4 implements event serialization, revision
upserts, delete lineage/visibility recalculation, and worker-health separation from API
readiness.

## Ordered task sequence

1. [E8-T1: Confirm channel identity and access](tasks/E8-T1-confirm-channel-identity-and-access.md) — `in_progress` (secrets/live resolve still open).
2. [E8-T4: Revalidate geocoder for recurring ingestion](tasks/E8-T4-revalidate-geocoder-for-recurring-ingestion.md) — delivered under revision 2.
3. [E8-T2: Implement secure Telethon session and backfill](tasks/E8-T2-implement-secure-telethon-session-and-backfill.md) — delivered under revision 3.
4. [E8-T3: Implement live new/edit/delete processing](tasks/E8-T3-implement-live-new-edit-delete-processing.md) — promoted under this revision.

Later revisions will sequence E8-T5 per the approved spike.

## Modules and contracts

- `wef_backend.features.ingestion.application.telegram_events`
- `wef_backend.features.ingestion.infrastructure.telethon_events`
- Extended `IngestionPersistencePort.persist_live_upsert` / `mark_source_deleted`
- Reuses E8-T2 Fake/Telethon clients and E3 persistence
- No public OpenAPI change; no schema migration; no worker Compose enablement

## Tests and checks

- Unit tests for new/edit/delete convergence, checkpoint non-rewind on older edits,
  queue serialization, Telethon adapters, worker-health vs API readiness
- `make lint` / typecheck / backend tests for the touched modules

## Rollout and limits

- No production worker enablement (E8-T5)
- Live Telethon event subscriptions require owner-supplied secrets (B-003)

## Approval checklist

- [x] Spike revision 2 is approved (AD-031).
- [x] Sequence contains only promoted E8-T1, E8-T4, E8-T2, and E8-T3.
- [x] No proposed task appears as executable work.
- [x] Safety limit: no worker Compose profile enablement; secrets remain owner-supplied.
