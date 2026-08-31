---
schema: ai-workflow/task@1
id: E8-T3
epic: E8
title: "Implement live new/edit/delete processing"
status: in_progress
revision: 1
priority: P2
size: L
milestone: M4
dependencies: [E8-T2, E8-T4]
requirement_ids: [P-006, P-007]
decision_ids: [ADR-003, ADR-005, ADR-006, ADR-007]
deferred_decision_ids: []
blocker_ids: [B-003]
source: "legacy-roadmap:E8-T3"
promotion:
  status: promoted
  target: tasks/E8-T3-implement-live-new-edit-delete-processing.md
  promoted_by: "Cursor Agent (autonomous epic mission under AD-009 continue)"
  promoted_at: "2026-08-21T08:15:35Z"
---

# E8-T3: Implement live new/edit/delete processing

## Outcome

Serialize channel-scoped new/edit/delete events through the shared E3 persistence
port so replayed events converge, edits create revisions, deletes preserve lineage
and hide public offers, and worker disconnects never gate API readiness.

## Acceptance

- [x] Replayed/duplicate events converge (fake client + upsert identity/checksum).
- [x] Edits preserve previous payload via revisions and update derived data.
- [x] Deletes mark `source_messages.deleted_at`, hide linked offers, and keep lineage.
- [x] Worker health is explicit and does not imply API unavailability.
- [x] Live Telethon subscription against a real authorized session (transport connected,
  consumer running, reconciliation running, verified channel `2180077318`).
- [ ] Production worker loop / Compose enablement (delivered under E8-T5; passive edit/delete evidence remains B-003).

## Scope delivered in revision 1

- `LiveTelegramEvent` / `LiveTelegramEventProcessor` / `LiveEventQueue`
- `persist_live_upsert` and `mark_source_deleted` on the ingestion persistence port
- Telethon event → inward event adapters (`telethon_events`)
- Deterministic fake-client tests for new/edit/delete convergence
- No worker Compose enablement; no public OpenAPI change

No real passive edit/delete callback arrived during the E15 or E8 observation windows
(`last_event_received_at` remained null). Real passive event semantics therefore remain
an explicit E8/M4 acceptance item; see
[B003 observation runbook](../B003_OBSERVATION_RUNBOOK.md). E15 proves that a missed
passive suffix is recovered by bounded source polling and that a stalled
consumer/reconciler cannot remain healthy while health evaluation is running.

## Dependencies and traceability

- Task dependencies: [E8-T2](E8-T2-implement-secure-telethon-session-and-backfill.md),
  [E8-T4](E8-T4-revalidate-geocoder-for-recurring-ingestion.md)
- Milestone: [M4](../../../milestones/M4-live-telegram-updates.md).
- Spike: [SPIKE.md](../SPIKE.md) revision 2.
- Plan: [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) revision 4.
