---
schema: ai-workflow/epic@1
id: E15
title: "Telegram ingestion reliability recovery"
status: done
milestones: [M4]
owner: owner
spike: SPIKE.md
implementation_plan: IMPLEMENTATION_PLAN.md
---

# E15: Telegram ingestion reliability recovery

## Outcome

Telegram remains the authoritative live source, and every source message after the
durable production checkpoint is eventually reconciled through the canonical ingestion
core even when passive update delivery, a worker task, the network, or a deployment
restart fails. Operators detect a real source gap promptly, recover it without a full
historical import, and can prove the result without exposing source text or secrets.

## Priority and selection

- **Operational priority at selection: blocker.** The workflow's highest formal task
  priority is `P0`, so every promoted task in this epic was `P0`.
- The owner selected E15 on 2026-08-27 after production missed the day's Telegram
  offers while Docker continued to report the listener as healthy.
- E15 took precedence over ordinary post-launch work until the M4 source-gap and
  outage-recovery evidence completed in PR #191.
- [B-003](../../operations/BLOCKERS.md#b-003-telegram-live-acceptance-evidence) is now
  narrowed to E8's real passive new/edit/delete and live-media acceptance; no E15 work
  remains under that blocker.

Priority and selection do not bypass the repository's approval gates.

## Approval state

- Epic workspace: `done`; all promoted tasks completed through green-CI PRs.
- [Research spike](SPIKE.md): revision 1, owner-approved under AD-039.
- [Implementation plan](IMPLEMENTATION_PLAN.md): revision 1, owner-approved under AD-040.
- E15-T1 is `done` through green-CI PR #189; E15-T2 is `done` through green-CI
  PR #190; E15-T3 is `done` through green-CI PR #191.

## Incident baseline

Read-only production inspection on 2026-08-27 established the following redacted facts:

- The production worker started at `2026-08-27T12:33:30Z`, remained connected, had
  zero container restarts, and Docker reported it healthy.
- PostgreSQL remained at Telegram message/checkpoint `29202`; the latest committed live
  run finished at `2026-08-26T18:09:59Z` and worker status classified it as stale.
- The channel contained 55 newer message records (`29203` through `29257`) published
  between `2026-08-27T13:21:36Z` and `13:25:34Z`. The production parser classified six
  text records as unit-offer candidates: `29203`, `29212`, `29221`, `29230`, `29240`,
  and `29250`.
- Production had persisted none of those messages and had created no live ingest run
  for them, placing the failure before canonical persistence.
- The production account was authorized, subscribed to the verified channel, and
  present in its dialogs. The deployed Telethon message conversion and NewMessage/
  MessageEdited filters accepted missed message `29203`.
- No duplicate production worker, current PostgreSQL advisory lock, restart, or
  database wait explained the gap.
- Existing logs cannot distinguish whether Telegram omitted the passive update or an
  unobserved Telethon/consumer failure discarded it. The worker CLI does not configure
  Telethon event logging, the consumer task is not supervised alongside the connection
  loop, and Docker health measures transport connectivity rather than source progress.

The investigation made no production writes, restarts, or backfills and did not retain
source text, contacts, credentials, or session material.

The bounded production repair, idempotency proof, controlled restart, worker-health
fire/clear rehearsal, and retained E8 limitations are recorded in
[PRODUCTION_EVIDENCE.md](PRODUCTION_EVIDENCE.md).

## Approved task sequence

1. [E15-T1: Supervise and observe the Telegram event pipeline](tasks/E15-T1-supervise-and-observe-event-pipeline.md) — P0/M; `done` through PR #189
2. [E15-T2: Add checkpoint-driven Telegram reconciliation](tasks/E15-T2-add-checkpoint-driven-reconciliation.md) — P0/L; `done` through PR #190
3. [E15-T3: Recover the production gap and prove outage recovery](tasks/E15-T3-recover-gap-and-prove-outage-recovery.md) — P0/M; `done` through PR #191

T1 makes failures fail visibly. T2 makes passive events a latency optimization rather
than the completeness boundary. T3 performs bounded recovery only after those controls
are reviewed and deployed, then records the evidence needed by E8, B-003, and M4.

## Scope controls

- Preserve the existing backend-authoritative parsing, idempotency, provenance,
  visibility, geocoding, media, and checkpoint contracts.
- Do not add a queue, broker, second worker replica, new production service, or new
  dependency without explicit spike/implementation-plan approval.
- Never log Telegram source text, contacts, credentials, session strings, raw update
  payloads, or unbounded high-cardinality labels.
- Keep public API readiness independent of Telegram availability while making worker
  liveness and source freshness truthful and actionable.
- Treat passive NewMessage/Edit/Delete events as low-latency signals, not a guarantee
  of source completeness.
- Keep media-download completion in E8-T2 unless the approved spike demonstrates that
  a narrowly required E15 change cannot be separated.
- Do not claim the missed range recovered until database/source reconciliation and
  public projection consequences are explicitly verified.

## Completion boundary

E15 is complete only when all promoted tasks satisfy the workflow definition of done,
the missed production range is reconciled, startup/reconnect/outage gaps self-heal in a
bounded period, a dead event consumer cannot remain healthy, required alerts fire and
recover in rehearsal, and B-003/M4 are updated with redacted durable evidence.

This boundary is satisfied. E15 closes without claiming E8's still-unobserved real
passive edit/delete callbacks, live media acquisition, M4 completion, or backup recovery.
