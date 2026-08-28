# E15 production recovery evidence

This record contains only release identifiers, message IDs, aggregate counts, health
states, and timestamps. It contains no source text, contacts, credentials, session
material, raw payloads, or database secrets.

## Observation boundary and release

- Observation date: 2026-08-28 UTC.
- Deployed release: `7184cc2d67aafadc654c26fa26fd039ca4390ab2`
  (E15-T2, PR #190).
- Green deployment workflow: GitHub Actions run `33209149677`; candidate verification,
  immutable image publication, activation, and production smoke all succeeded.
- Immutable rollback release: `b4b3d6112f271633127d4002110ed0ba5924937e`
  (E15-T1, PR #189).
- Stable Telegram head used for the recovery boundary: `29335`.
- PostgreSQL accepted connections, public HTTPS readiness returned `200`, and the
  independently hosted AI Forecast endpoint on port 3000 returned `200`.

## Automatic reconciliation and bounded repair

Before E15-T2 deployed, the live checkpoint was `29258`; the database contained 78
source messages above incident checkpoint `29202`, spanning `29258` through `29335`.
After the new worker started, immediate overlap reconciliation advanced the durable
checkpoint to the observed remote head `29335`, reported remote/local `aligned`, and
persisted 19 previously missing messages (`29239` through `29257`). At that point the
database contained 97 rows spanning `29239` through `29335`, leaving the 36 older IDs
`29203` through `29238` outside the configured 20-message overlap.

With the singleton worker stopped, the approved existing operator command ran from
checkpoint `29202` with overlap `0` and limit `500`. Public HTTPS and Forecast both
remained `200` while the worker was stopped.

First bounded result:

```text
checkpoint=29335 seen=133 created=4 revised=0 skipped_non_candidate=32 unchanged=97
```

The global canonical counters changed as follows:

| Counter | Before | After first replay | After identical replay |
| --- | ---: | ---: | ---: |
| source messages | 27,850 | 27,886 | 27,886 |
| source revisions | 28,035 | 28,071 | 28,071 |
| offers | 3,056 | 3,060 | 3,060 |
| offer-source links | 3,085 | 3,089 | 3,089 |
| contact points | 129 | 129 | 129 |
| maximum source message ID | 29,335 | 29,335 | 29,335 |

The identical second replay reported `seen=133`, `created=0`, `revised=0`,
`skipped_non_candidate=0`, `unchanged=133`, and checkpoint `29335`. It therefore
changed none of the measured canonical counters and did not move the checkpoint
backward.

## Canonical and duplicate checks

- All 133 IDs from `29203` through `29335` exist; missing count at the stable boundary
  is zero.
- Sampled incident candidates `29203`, `29212`, `29221`, `29230`, `29240`, and
  `29250` each have exactly one source message, at least one immutable revision, and
  exactly one linked canonical offer.
- Duplicate counts are zero for channel/message identity, message/revision number,
  offer/revision linkage, and offer/kind/contact fingerprint.
- The complete boundary contains 133 source messages, 208 immutable revisions, 14
  distinct linked offers, and 27 offer-source links.
- All 14 linked offers remain `needs_review`; their shared location is accepted. E15
  did not perform manual visibility promotion.
- This text-first path created no scoped contact points or media assets. Media download
  acceptance remains open under E8 and is not implied by this recovery.

## Restart and health-signal rehearsal

The worker returned `running/healthy` after the repair and recorded transport connected,
consumer running, reconciliation running, remote head `29335`, local checkpoint `29335`,
and remote gap false.

A controlled worker restart returned Docker health to `healthy` in about ten seconds.
Its immediate reconciliation completed at `2026-08-28T20:52:55Z`, remained aligned at
`29335`, and public HTTPS plus Forecast both remained `200`.

For the failure-signal proof, only the worker application child was paused so Docker's
healthcheck process continued to run. The pause began at `2026-08-28T20:56:07Z`;
Docker changed the worker from `healthy` to `unhealthy` after 91 seconds while public
readiness remained `200`. The child resumed at `2026-08-28T20:57:38Z`; health cleared
to `healthy` within 20 seconds, immediate reconciliation completed, and status again
reported consumer/reconciliation running with remote/local `29335` and no gap.

An earlier whole-container `SIGSTOP` probe was intentionally not counted as acceptance
evidence: suspending every process also prevented Docker from executing the container's
healthcheck, so the last health label did not change. A cleanup trap resumed the
container. The application-child rehearsal above exercises the production failure mode
the E15 controls own while leaving the independent health evaluator operational.

No real passive new/edit/delete callback arrived during the observation window
(`last_event_received_at` and `last_event_committed_at` remained null). Real passive
event semantics therefore remain an explicit E8/M4 acceptance item; E15 proves that a
missed passive suffix is recovered by bounded source polling and that a stalled
consumer/reconciler cannot remain healthy while health evaluation is running.

## Operational safety

- A count-only scan of worker logs since the E15-T2 deployment found zero matches for
  credential/session, database URL/password, source-text, raw-payload, or encrypted
  contact field markers. Raw logs were not copied into this evidence.
- Production limits remained configured: API 768 MiB/1 CPU/256 PIDs; web 512 MiB/0.75
  CPU/192 PIDs; Telegram worker 512 MiB/0.5 CPU/128 PIDs; PostgreSQL 2 GiB/1.5 CPU/256
  PIDs. All retain `unless-stopped` restart policy.
- Recovery used only the deployed `wef-telegram-backfill`, worker status, Compose, and
  database aggregate-query paths. No ad-hoc repair script, raw export, or source content
  was introduced.
- Persistent data is still not a backup under ADR-015; this evidence makes no backup or
  host-loss recovery claim.
