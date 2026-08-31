# E8 live media production evidence

This record contains only release identifiers, message IDs, aggregate counts, health
states, and timestamps. It contains no source text, contacts, credentials, session
material, raw payloads, or database secrets.

## Observation boundary and release

- Observation date: 2026-08-31 UTC.
- Deployed release: `b71c99fd59852ed6bc08ef53720d7c4d6bc63dc7`
  (E8-T2 live media, PR #243).
- Green deployment workflow: GitHub Actions run `33420585501`; candidate verification,
  immutable image publication, activation, and production smoke all succeeded.
- Worker `runtime_health.release_sha` reported `b71c99fd5985` after restart.
- Public HTTPS readiness returned `200`.

## Reconciliation with live media acquisition

After the new worker started, overlap reconciliation advanced the durable checkpoint
from the prior boundary through observed remote head `29434`. For the 20 message IDs
`29415` through `29434`, the worker:

- downloaded photo bytes to the bounded temp path (`/tmp/wef-telegram-media/<id>/0.jpg`);
- persisted restricted originals under the configured originals root; and
- created public derivative variants (`thumbnail_jpeg_v1`, `thumbnail_webp_v1`) with
  timestamps between `2026-08-31T17:46:29Z` and `2026-08-31T17:46:32Z`.

Aggregate checks on database `wef_hist_candidate`:

| Check | Result |
| --- | --- |
| Distinct reconciled IDs with new media assets (`29415`–`29434`) | 20 |
| Worker remote/local alignment at observation | aligned at `29434` |
| Transport connected / consumer running | true |
| Passive new/edit/delete callback during window | none observed |

This reconciliation path proves live media download and storage through the shared E3
pipeline. It does not by itself prove passive edit/delete semantics or latency-bound
new-message callbacks; those remain under B-003.

## Residual acceptance

- No real passive edit or delete callback was observed during this window.
- Closing B-003 still requires a safely observable edit/delete sequence (organic or
  explicitly coordinated). Do not create or alter source-channel posts without separate
  authority. When an event occurs, follow [B003 observation runbook](B003_OBSERVATION_RUNBOOK.md).

## Passive edit/delete watch (ongoing)

- Watch started: 2026-08-31 UTC after deploy `ab4f17aba120138de6e7a353c78202601521047f`
  (PR #250 passive-event monitor).
- NUC cron polls `check_telegram_passive_events.py` every 15 minutes via
  `releases/current` and appends to `/home/nuc/wef/state/passive-event-check.log`.
- Manual probe at `2026-08-31T18:17Z`: worker release `ab4f17a`, remote/local head
  `29434`, transport connected, consumer running, `last_event_received_at` null,
  monitor exit `0`.
- B-003 closure trigger: monitor exit `2` or non-null `last_event_received_at` plus
  runbook capture steps for edit/delete semantics.
