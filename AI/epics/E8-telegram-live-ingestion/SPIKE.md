---
schema: ai-workflow/spike@1
epic: E8
title: "Future Telegram live ingestion research"
status: awaiting_approval
revision: 2
owner: owner
research_only: true
code_allowed: false
decision_ids: [ADR-003, ADR-005, ADR-006, ADR-007, ADR-010, ADR-015]
domain_docs: [ingestion, data, operations, security]
proposed_task_ids: [E8-T1, E8-T2, E8-T3, E8-T4, E8-T5]
approval:
  required_role: owner
  status: pending
  decided_by: null
  decided_at: null
  approved_revision: null
  evidence: null
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# Spike: Future Telegram live ingestion

> Revision 2 is completed research awaiting owner approval. It authorizes no production
> code, scaffold, migration, infrastructure/configuration change, generated executable
> artifact, prototype, proof branch, or disposable proof code.

## Question

How should a single hardened Telethon worker reconcile the historical checkpoint and process new, edited, and deleted posts through the shared ingestion core without changing public contracts or leaking session credentials?

## Context and constraints

- Production activation starts only after M3 and D-003 channel/access confirmation.
- Credential-free implementation and deterministic tests may precede M3 only after this
  spike, promoted tasks, and an implementation plan receive their separate approvals.
- D-002 must be revalidated for recurring geocoding; public Nominatim cannot be the recurring production dependency.
- One worker replica owns the session/checkpoint lock and persists source state before advancing checkpoints.
- Telegram disconnects, flood waits, edits, deletes, and session rotation must not make the public API unavailable.
- Historical and live adapters stop at the same source-neutral boundary. E3-T2 must supply
  the persistence/reprocessing contract before E8-T2, and E3-T3 must supply the provider
  abstraction/cache before E8-T4.

Governing domains:

- [Ingestion](../../ingestion/README.md)
- [Data](../../data/README.md)
- [Operations](../../operations/README.md)
- [Security](../../security/README.md)

Governing decisions and deferred gates:

- [ADR-003](../../decisions/adr/ADR-003-do-not-infer-current-availability.md)
- [ADR-005](../../decisions/adr/ADR-005-postgresql-postgis.md)
- [ADR-006](../../decisions/adr/ADR-006-shared-ingestion-core.md)
- [ADR-007](../../decisions/adr/ADR-007-mounted-media-storage-interface.md)
- [ADR-010](../../decisions/adr/ADR-010-isolate-wef-shared-nuc.md)
- [ADR-015](../../decisions/adr/ADR-015-defer-backups.md)
- [D-002](../../decisions/deferred/D-002-recurring-geocoding-provider.md)
- [D-003](../../decisions/deferred/D-003-telegram-channel-access.md)

## Research method

Review verified source-link identity, Telethon session/event/backfill behavior, source checkpoint overlap, grouped media IDs, idempotent persistence, delete visibility, geocoder quotas, worker locking, monitoring, and rotation runbooks.

Research outputs must remain non-executable Markdown. Any data inspection must preserve source privacy and may not copy real source payload, contacts, credentials, sessions, or media into this artifact.

## Evidence

### Existing application and operational contracts

- ADR-006 requires historical and live adapters to feed the same canonical ingestion core.
- The historical adapter already emits the source-neutral `RawMessage` contract with stable
  source identity, checksum, edited timestamp, media descriptors, and `media_group_id`.
- The ingestion pipeline requires source/revision persistence and checkpoint advancement in
  one committed transaction. It specifies at-least-once delivery, overlap reconciliation,
  revision preservation, delete lineage, and bounded media handling.
- Production delivery already reserves one backend-image worker command, an internal network,
  a deploy-managed secret directory, and a single-replica operational boundary. The worker
  is deliberately absent from current Compose files.
- D-003 verifies `https://t.me/elestate_warszawa` and the public
  `https://t.me/elestate_warszawa/{message_id}` pattern, but no Telegram API ID/hash or
  authorized session is configured in GitHub Actions as of 2026-08-13.
- D-002 selects no recurring provider by itself. E3-T3 must first implement and measure the
  provider-neutral cache path; E8-T4 then revalidates the selected provider for continuous
  low-volume use. Public Nominatim remains ineligible for recurring jobs.

### Telethon behavior reviewed

- Telethon session files and
  [string sessions](https://docs.telethon.dev/en/stable/concepts/sessions.html) contain the
  authorization key and must be treated as account credentials. A string session can be
  loaded without writing a session database, but exposing the string grants account access.
- Session/entity state includes access hashes. Startup must resolve the configured public
  username with the authenticated client, then compare the numeric channel ID and title with
  non-secret expected configuration before any checkpoint or media write.
- [`iter_messages`](https://docs.telethon.dev/en/stable/modules/client.html#telethon.client.messages.MessageMethods.iter_messages)
  supports exclusive `min_id`/`max_id` bounds, oldest-first `reverse` iteration, explicit
  pacing, and bounded limits. The durable checkpoint therefore means the highest source
  message ID whose complete unit of work committed; replay starts with a configured overlap
  below that checkpoint and still converges by source identity/checksum.
- Telethon can auto-sleep for flood waits below its threshold. The worker instead needs one
  explicit policy that records the wait category/duration, sleeps for Telegram's supplied
  duration, and never blind-retries or advances the checkpoint while persistence is
  uncertain.
- `NewMessage` and `MessageEdited` events expose message data suitable for the same adapter
  conversion. `MessageDeleted` exposes deleted IDs but
  [is not guaranteed for every deletion](https://docs.telethon.dev/en/stable/modules/events.html#telethon.events.messagedeleted.MessageDeleted)
  and may lack chat context outside channels. Channel-scoped handlers reduce ambiguity but
  do not remove the delivery gap, so a bounded periodic overlap/reconciliation pass is
  mandatory.
- Live `grouped_id` remains the authoritative album key. Event callbacks must serialize work
  through one channel queue so album/media persistence, revisions, and checkpoints cannot
  race even if Telethon dispatches callbacks concurrently.

These are documentation and API facts, not evidence that a connection, backfill, event,
provider, deployment, or acceptance check has run.

## Required access and secret contract

- Use one dedicated, least-privilege Telegram user account that can read the public channel.
  A bot token is not a substitute unless a later approved revision proves equivalent history
  and edit/delete access.
- The owner supplies API ID, API hash, and an authorized Telethon string session only through
  GitHub Actions secrets. Deployment writes service-scoped mode-`0600` files beneath the
  active release secret directory; only the worker mounts them read-only.
- The worker reads secret files without echoing values, command-line arguments, serialized
  settings, exception context, health output, or generated Compose configuration. API, web,
  migrations, and CI never receive Telegram credentials.
- Session bootstrap and rotation are explicit operator commands in a controlled environment,
  never container startup behavior. Rotation stops the worker, atomically replaces the
  session file, verifies channel identity/checkpoint, starts a bounded overlap, and then
  revokes the old authorization.
- B-003 remains active until the expected numeric channel ID/title, operating owner, account,
  API credentials, authorized session, and real new/edit/delete observations are recorded.

## Recommended design

Run exactly one asynchronous Telethon worker from the backend image:

1. Load the session and API credentials from worker-only secret files.
2. Acquire a PostgreSQL advisory lock derived from the configured numeric channel ID. Exit
   unready without connecting when another owner holds the lock.
3. Resolve the username and fail closed if numeric ID/title differ from expected values.
4. Reconcile a bounded overlap, then backfill oldest-to-newest from the durable checkpoint.
5. Convert each source message at the Telethon infrastructure boundary and invoke the same
   E3 application persistence/reprocessing port used by historical import.
6. Commit source/revision/canonical effects and checkpoint in one database transaction before
   the worker records the event as committed.
7. Subscribe only to the verified channel's new/edit/delete events. New/edit events reuse the
   message path; deletes invoke an inward-owned deletion use case that preserves source
   lineage and recomputes derived visibility without inventing an availability boolean.
8. On reconnect or periodically, repeat a bounded overlap/reconciliation pass. A disconnect
   degrades worker freshness only; it never changes API readiness.

The session remains outside PostgreSQL so database access does not grant Telegram account
access. Checkpoints, ingest/reconciliation runs, source revisions, deletions, last
received/committed timestamps, connection state, and redacted retry categories remain in
PostgreSQL because they must survive worker replacement.

Media download is bounded by count, bytes, timeout, and concurrency. It writes temporary
files only to a worker-owned temporary path, then hands successful content to the existing
storage interface. Missing, expired, oversized, or unsupported media is recorded without
blocking unrelated messages. No source path becomes a public URL.

## Options considered

- **Selected:** one Telethon adapter/worker over the E3 source-processing and checkpoint
  contracts, with bounded media, a PostgreSQL ownership lock, and at-least-once overlap.
- **Rejected:** a live-only parser/persistence path. It would duplicate canonicalization,
  uncertainty, geocoding, visibility, and public behavior contrary to ADR-006.
- **Rejected:** multiple active replicas or an in-memory-only lock. They can race session use,
  checkpoints, album processing, and media writes across containers.
- **Rejected:** session files in images, environment dumps, the database, or shared API
  mounts. Each unnecessarily broadens credential access and rotation blast radius.
- **Rejected:** treating Telethon's update stream as an exactly-once log. Delete events are
  not fully reliable and disconnect gaps require bounded reconciliation.

## Task and gate refinement

- **E8-T1** owns the non-secret expected channel identity, dedicated-account/operating-owner
  decision, worker-only secret contract, redacted verification command, and real test-channel
  evidence. D-003 may be resolved during planning once those decisions are approved; missing
  secret values keep T1 acceptance open but do not belong in repository artifacts.
- **E8-T4** remains independently reviewable after E3-T3. It revalidates the already-selected
  provider for recurring use and defines quota/error/defer observability; it does not build a
  second geocoder or choose from scratch.
- **E8-T2** depends on E8-T1, E8-T4, and E3-T2. It owns the Telethon dependency, secret/session
  loading, entity verification integration, advisory ownership lock, bounded backfill/media,
  and checkpoint reconciliation. It must not invent persistence before E3-T2.
- **E8-T3** depends on E8-T2 and E8-T4. It owns new/edit/delete subscriptions, serialization,
  revision/delete behavior, reconnect overlap, and deterministic event/replay tests.
- **E8-T5** depends on E8-T3 and E8-T4. It owns disabled-by-default local/production Compose,
  deploy secret transfer, worker health/staleness alerts, export-checkpoint reconciliation,
  session rotation, outage rehearsal, and the production-activation gate.

The roadmap's M3 prerequisite is refined from a code-development gate to an **E8-T5
production-activation gate**. T1-T4 may be implemented and tested without live production
activation after all ordinary workflow approvals. T5 cannot complete, the worker remains
disabled, and the epic cannot become `done` until M3, B-003/D-003, D-002, dependency, and
real operational evidence all pass.

The direct implementation order is E8-T1, E8-T4, E8-T2, E8-T3, E8-T5. An incomplete parent
may authorize only a valid stacked dependency gate; no descendant can become `done` or merge
before every dependency becomes `done`.

## Proposed task boundaries

- [E8-T1: Confirm channel identity and access](proposed-tasks/E8-T1-confirm-channel-identity-and-access.md) — candidate boundary for spike refinement.
- [E8-T2: Implement secure Telethon session and backfill](proposed-tasks/E8-T2-implement-secure-telethon-session-and-backfill.md) — candidate boundary for spike refinement.
- [E8-T3: Implement live new/edit/delete processing](proposed-tasks/E8-T3-implement-live-new-edit-delete-processing.md) — candidate boundary for spike refinement.
- [E8-T4: Revalidate geocoder for recurring ingestion](proposed-tasks/E8-T4-revalidate-geocoder-for-recurring-ingestion.md) — candidate boundary for spike refinement.
- [E8-T5: Production reconciliation and worker alerting](proposed-tasks/E8-T5-production-reconciliation-and-worker-alerting.md) — candidate boundary for spike refinement.

No candidate above may appear in an executable implementation-plan sequence while it remains under `proposed-tasks/`.

## Risks and open questions

- The authorized account may not receive every required event. T1 must exercise real
  new/edit/delete behavior; T3/T5 overlap reconciliation remains required even when it does.
- A session leak grants Telegram account access. `_FILE` loading, narrow mounts, redacted
  errors, repository/image scans, and rotation rehearsal reduce but do not eliminate this
  single-host risk.
- Telegram may impose long waits or access restrictions. Exact flood-wait handling and
  persisted progress prevent hot loops and false advancement; no bypass is acceptable.
- Deletes cannot be inferred solely from message-ID gaps. Explicit events and bounded
  reconciliation must preserve uncertainty rather than silently hiding offers.
- E3-T2 and E3-T3 are external dependencies owned outside this epic. E8-T2/T4 stop if their
  concrete contracts or approved scope differ from this spike.
- Provider terms/quota or quality may change. E8-T4 records dated evidence and keeps
  cache/defer semantics provider-neutral.
- The single host and deferred backups can lose database, media, and the active session.
  E8 adds restart/rotation behavior but must not claim disaster recovery.
- Exact alert transport and thresholds remain an implementation-plan decision based on the
  monitoring mechanism available after E3/M3; last-received/committed/connected timestamps
  and stale classification are required regardless of transport.

## Invalidation triggers

- A change to this epic's outcome, accepted architecture/dependency direction, public or persisted contracts, security model, ingestion semantics, or deployment topology.
- A new external dependency or service that changes data handling, operations, licensing, secrets, or replacement paths.
- Evidence that a listed task boundary cannot remain independently reviewable or that a roadmap dependency is incomplete.

## Exit checklist

- [x] The bounded question is answered with evidence and uncertainty distinguished.
- [x] Governing domain documents and decisions are reviewed and linked.
- [x] Options, recommendation, risks, and open questions are complete.
- [x] Proposed task scope, acceptance, dependencies, priority/size, and traceability are refined.
- [x] No production or disposable proof code was created.
- [x] `revision` represents the material content being submitted.
- [x] Status is changed to `awaiting_approval` while approval remains `pending`.

## Owner decision

The owner records the decision only in the YAML `approval` object. Approval of revision 2
would permit task refinement/promotion and implementation planning only; it would not permit
code or live Telegram access.
