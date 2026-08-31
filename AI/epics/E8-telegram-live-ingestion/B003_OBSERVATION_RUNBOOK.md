# B-003 passive edit/delete observation runbook

Use this runbook when a **real** channel post is edited or deleted and E8 must capture
redacted production evidence to close B-003, E8-T3, E8-T5, and M4. It records only
release identifiers, message IDs, aggregate counts, health states, and timestamps.

Do **not** create, edit, or delete source-channel posts unless the operating owner has
explicitly authorized a coordinated test.

## Preconditions

- Production worker is running (`telegram-worker` service in `wef-production`).
- Transport is connected and the consumer is running (`wef-telegram-worker-status`).
- You know the affected `external_message_id` (numeric Telegram message id only).

## 1. Capture worker status (before and after)

On the NUC:

```bash
docker compose -p wef-production exec -T telegram-worker wef-telegram-worker-status
```

Record:

- `runtime_health.release_sha`
- `runtime_health.last_event_received_at` — must become non-null for a **passive**
  callback (reconciliation alone does not satisfy B-003)
- `runtime_health.last_event_committed_at`
- `runtime_health.transport_connected` and `consumer_running`
- `reconciliation.status` and checkpoint fields

Run the command again after the event settles (within a few minutes).

## 2. Confirm passive event processing in logs

Search recent worker logs for a committed passive event (no source text):

```bash
docker compose -p wef-production logs telegram-worker --since 30m \
  | grep telegram_event_committed
```

Expect `event_kind=edit` or `event_kind=delete` for B-003 closure. A passive
`event_kind=new` is useful context but does not alone close the edit/delete gate.

## 3. Verify database semantics (aggregate only)

Use database `wef_hist_candidate` (not `wef`):

```bash
docker compose -p wef-production exec -T db psql -U wef -d wef_hist_candidate
```

### Edit evidence

Replace `<ID>` with the numeric external message id.

```sql
SELECT sm.external_message_id,
       count(smr.id) AS revision_count,
       max(smr.revision_number) AS max_revision
FROM source_messages sm
JOIN source_message_revisions smr ON smr.source_message_id = sm.id
WHERE sm.external_message_id = <ID>
GROUP BY sm.external_message_id;
```

Pass: at least two revisions after an edit; prior revision rows remain immutable.

### Delete evidence

```sql
SELECT sm.external_message_id,
       sm.deleted_at IS NOT NULL AS deleted,
       count(DISTINCT os.offer_id) AS linked_offers
FROM source_messages sm
LEFT JOIN offer_sources os
  ON os.source_message_id = sm.id AND os.relationship = 'primary'
WHERE sm.external_message_id = <ID>
GROUP BY sm.external_message_id, sm.deleted_at;
```

Pass: `deleted` is true; linked offers are hidden from public catalog semantics
(verify offer visibility separately if needed; do not copy listing text).

## 4. Record evidence

Append a dated section to
[PRODUCTION_EVIDENCE.md](PRODUCTION_EVIDENCE.md) using the same redaction rules as
[E15 production evidence](../E15-telegram-ingestion-reliability/PRODUCTION_EVIDENCE.md):

- release SHA and deploy run id (if a new deploy occurred)
- observation timestamps
- affected external message id(s) only
- passive `last_event_received_at` / `last_event_committed_at` values
- aggregate revision/delete counts
- explicit statement that no source text, contacts, or secrets were copied

Then update:

- [BLOCKERS.md](../../operations/BLOCKERS.md) — move B-003 to resolved or narrow further
- [E8-T3 task](tasks/E8-T3-implement-live-new-edit-delete-processing.md) — mark `done`
- [E8-T5 task](tasks/E8-T5-production-reconciliation-and-worker-alerting.md) — mark `done`
- [M4 milestone](../../milestones/M4-live-telegram-updates.md) — check exit evidence

## 5. What does not close B-003

- Reconciliation-only catch-up of new message ids (checkpoint polling).
- Backfill CLI runs (`wef-telegram-backfill`).
- Inferring deletion from absence (forbidden by ADR-003).
- Staging/local fake-client tests (already satisfied in CI).

## Current observation state (2026-08-31 UTC)

- Release `b71c99f` deployed; checkpoint aligned at `29434`.
- Live media acquisition verified for ids `29415`–`29434`.
- `last_event_received_at` remains null; no passive edit/delete observed yet.

## Optional cron monitor (NUC)

Poll worker status and exit non-zero when a passive event appears so operators can
capture evidence promptly:

```bash
python3 /home/nuc/wef/releases/current/scripts/deploy/check_telegram_passive_events.py
```

Exit codes: `0` healthy/no passive event; `2` passive event detected (run capture steps
above); `1` error or unhealthy worker. Schedule every 15 minutes only after placing the
script on the NUC from a deployed release checkout.
