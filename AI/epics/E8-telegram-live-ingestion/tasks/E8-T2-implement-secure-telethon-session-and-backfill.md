---
schema: ai-workflow/task@1
id: E8-T2
epic: E8
title: "Implement secure Telethon session and backfill"
status: in_progress
revision: 1
priority: P2
size: L
milestone: M4
dependencies: [E8-T1, E3-T2, E8-T4]
requirement_ids: [P-006, P-007]
decision_ids: [ADR-005, ADR-006, ADR-007]
deferred_decision_ids: []
blocker_ids: [B-003]
source: "legacy-roadmap:E8-T2"
promotion:
  status: promoted
  target: tasks/E8-T2-implement-secure-telethon-session-and-backfill.md
  promoted_by: "Cursor Agent (autonomous epic mission under AD-009 continue)"
  promoted_at: "2026-08-21T07:46:50Z"
---

# E8-T2: Implement secure Telethon session and backfill

## Outcome

Secure Telethon session loading, entity verification against the E8-T1 identity, advisory
ownership lock, and a restartable/idempotent bounded backfill through the shared E3
persistence port—without enabling the production worker or changing public contracts.

## Acceptance

- [x] A test-channel (fake-client) backfill is restartable and idempotent.
- [x] Session values never enter logs/API/repository/image (file-only load, redacted CLI).
- [x] Backfill reconciles message counts/checkpoint (`ingest_runs.checkpoint_json` via
  `external_message_id` as the live cursor).
- [ ] Live Telethon acceptance against a real authorized session (blocked on B-003).
- [ ] Bounded media download to worker temp then storage (text-first backfill shipped;
  media bytes remain follow-up within this task or a tight successor).

## Scope delivered in revision 1

- `telethon` dependency (spike-selected).
- Worker secret loader (`mode 0600` api_id/api_hash/session files).
- `TelegramLiveClientPort`, Fake client, Telethon adapter (`flood_sleep_threshold=0`).
- Entity verify against non-secret `TelegramChannelIdentity`.
- `LiveTelegramBackfill` + `wef-telegram-backfill` CLI.
- No Compose worker enablement; no production activation (E8-T5).

## Dependencies and traceability

- Task dependencies: [E8-T1](E8-T1-confirm-channel-identity-and-access.md),
  [E3-T2](../../E3-database-geocoding-media/tasks/E3-T2-implement-idempotent-persistence-and-reprocessing.md),
  [E8-T4](E8-T4-revalidate-geocoder-for-recurring-ingestion.md)
- Milestone: [M4](../../../milestones/M4-live-telegram-updates.md).
- Spike: [SPIKE.md](../SPIKE.md) revision 2.
- Plan: [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) revision 3.
