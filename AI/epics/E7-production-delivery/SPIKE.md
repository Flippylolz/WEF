---
schema: ai-workflow/spike@1
epic: E7
title: "Docker/GitHub production delivery research"
status: approved
revision: 4
owner: owner
research_only: true
code_allowed: false
decision_ids: [ADR-005, ADR-006, ADR-007, ADR-008, ADR-009, ADR-010, ADR-013, ADR-014, ADR-015, ADR-017, ADR-018, ADR-019, ADR-020]
domain_docs: [operations, governance, security, data, ingestion]
proposed_task_ids: [E7-T1, E7-T2, E7-T3, E7-T4, E7-T5, E7-T6, E7-T7, E7-T8, E7-T9, E7-T10]
approval:
  required_role: owner
  status: approved
  decided_by: Flippylolz
  decided_at: "2026-08-15T16:49:02Z"
  approved_revision: 4
  evidence: "Owner reviewed the E7 revision-4 spike PR, replied LGTM, and explicitly directed both prepared PRs to merge in the Codex task"
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# Spike: Docker/GitHub production delivery

> Revision 4 is owner-approved research. It prioritizes the verified historical snapshot transfer while preserving the revision-3 shared-edge design. Spike approval authorizes task refinement and implementation planning only; it authorizes no production code, transfer tooling, bundle creation, server mutation, or data activation.

## Revision 4 change control

- Preserve completed E7-T1 through E7-T4 and the approved revision-3 Nginx/Certbot direction.
- Pause E7-T8/E7-T9 implementation while E7-T6 is refined, as explicitly directed by the owner on 2026-08-15.
- Replace E7-T6's obsolete raw-export/server-reprocessing approach with a materialized snapshot transfer from the verified E3-T5 terminal state.
- Separate transfer and fully reconciled candidate staging from public historical-data activation. [ADR-019](../../decisions/adr/ADR-019-anonymous-http-production-rehearsal.md) permits only synthetic data on interim HTTP and still requires the E7-T10 HTTPS and E7-T7 sensitive-feature gates before historical data becomes public.
- Keep E7-T5 backup/recovery deferred. Retaining the old database, media roots, and candidate on the same NUC is rollback material, not a backup claim.

## Question

How should the verified E3-T5 database/media state be packaged, transferred, restored into a production candidate, reconciled, and retained for later HTTPS-gated activation without transferring the raw export, rerunning providers or transformations, overwriting production identity/session state, or interfering with other NUC workloads?

## Current verified source state

The local E3-T5 result was rechecked after merged [PR #66](https://github.com/Flippylolz/WEF/pull/66):

- Source checksum: `2399a88c70253c3f34b6ab73c423e094e7eb5f179ee9392b87ed715a74c6649d`.
- Pipeline/schema: `e3-complete-v2` / `20260815_0008`.
- Canonical data: 27,170 source messages, 27,171 revisions, 2,994 offers, 792 locations, and 474 accepted locations.
- Provider evidence: 665 succeeded and 9 no-result attempts; transfer must make zero hosted provider calls.
- Logical media dispositions: 23,173 stored, 3,952 unassociated, 55 missing, and 55 unsupported placeholders.
- Physical media: 24,532 restricted originals totaling 2,190,294,326 bytes and 49,059 public derivatives totaling 5,007,224,426 bytes; database object counts and filesystem counts match exactly.
- A terminal dry run reports 27,170 unchanged records, zero new/changed records, zero pending locations, zero media work, and zero malformed records.

These aggregates and identities may enter a non-sensitive manifest. Raw rows, contact values, source-relative paths, local filesystem paths, reports containing source detail, credentials, and media bytes must not enter Git, GHCR, Actions artifacts, logs, or image layers.

## Current production observations

Read-only checks on 2026-08-15 found:

- Production remains healthy on release `e03251a7714a4bd77c378b88d09dd9b336f70492`, schema `20260815_0006`, with 0 source messages, 5 synthetic offers, 4 synthetic locations, and 0 users.
- The NUC has approximately 872 GB free disk and 6.1 GiB available memory; exact thresholds must be rechecked immediately before each mutation.
- WEF, AI Forecast, DuckDNS, and WireGuard projects are healthy. E7-T6 may target only `/home/nuc/wef` and the `wef-production` boundary.
- The automatic release for PR #66 failed before image publication because the host-only test database URL leaked into a Compose test container. Authorized hotfix [PR #67](https://github.com/Flippylolz/WEF/pull/67) must merge and deploy successfully before any candidate restore.
- Current public WEF traffic is interim HTTP on port 3100. ADR-019 forbids public historical-data activation at this stage even though a restricted, non-public candidate may be transferred and validated on the host.

All observations are point-in-time evidence, not assumptions for execution.

## Research method and primary references

The spike reviewed the merged E3-T5 implementation/evidence, E7 production manifests and rollback scripts, current production database aggregates and host capacity, the E7-T6 revision-2 proposal, ADR-019, and current PostgreSQL/rsync behavior:

- [PostgreSQL 17 pg_dump](https://www.postgresql.org/docs/17/app-pgdump.html) and [SQL dump guidance](https://www.postgresql.org/docs/17/backup-dump.html) document data-only/selective dumps and internally consistent snapshots.
- [PostgreSQL 17 CREATE DATABASE](https://www.postgresql.org/docs/17/sql-createdatabase.html) documents template cloning and its requirement that the source database have no other connections while cloning begins.
- [PostgreSQL 17 pg_restore](https://www.postgresql.org/docs/17/app-pgrestore.html) documents exit-on-error and single-transaction restore controls; E7-T6 still needs an application-specific conflict preflight because a generic restore does not prove same-key/same-content identity.
- The official [rsync manpage](https://download.samba.org/pub/rsync/rsync.1) documents retained partial files and whole-transfer `--info=progress2` reporting. Every transferred immutable component still requires an independently verified SHA-256.

Research outputs remain Markdown and aggregate/redacted evidence only.

## Options evaluated

### Re-run the raw import on production

Rejected. It transfers the most sensitive input, repeats parsing/geocoding/media work, consumes hosted quota, creates a second set of environment-dependent decisions, and contradicts the verified materialized E3-T5 boundary.

### Replace the whole production database and media roots

Rejected. It would overwrite or discard production users, sessions, synthetic/operational state, and unrelated future rows, and it provides no safe idempotent replay or bounded rollback.

### Restore selected rows directly into the live database

Rejected. A failed FK, checksum, conflict, migration, or media gate could leave partially visible state and would make rollback depend on destructive data repair.

### Transfer a selective snapshot and build an isolated candidate

Recommended. It preserves production identity/session state, allows complete conflict and reconciliation gates before activation, supports same-host rollback, and avoids every provider/parser/transform side effect.

## Proposed revision 4 architecture

### 1. Immutable local transfer bundle

E7-T6 should build one ignored, mode-`0600`, checksum-addressed bundle outside every Git/build/artifact context. It contains:

- A selective, data-only PostgreSQL component for catalog and ingestion-owned tables at migration head `20260815_0008`.
- Restricted-original and public-derivative archive components created only from application-owned E3-T5 storage, not from the raw export tree.
- A non-sensitive canonical manifest recording bundle format, source checksum, pipeline/release/schema identities, terminal aggregate counts, table row counts, media object counts/bytes, and a SHA-256/size/mode for every component and logical media object.

The selected database scope includes `locations`, `offers`, `source_channels`, `source_messages`, `source_message_revisions`, `developments`, `offer_sources`, `ingest_runs`, `complete_import_runs`, `provider_daily_budgets`, `provider_attempts`, `geocode_results`, `geocode_miss_claims`, `location_geocode_selections`, `stored_media_objects`, `media_assets`, `media_disposition_attempts`, `media_derivatives`, `media_derivative_attempts`, and `offer_media`.

The component explicitly excludes `users`, `auth_sessions`, `e0_proof_estates`, `alembic_version`, credentials, local paths, generated detailed reports, raw export files, and source-relative media. Terminal-state validation must reject an active import lease, active geocode claim, pending provider work, or mismatched selected-review/media lineage before packaging.

Bundle creation is fail-closed and non-overwriting. Re-running with the same inputs must produce the same logical manifest; a changed component creates a new bundle identity rather than mutating an existing bundle.

### 2. Dry run and capacity gate

Before writing a bundle, the operator receives a progress display and exact counts for:

- selected rows per table;
- logical/physical media objects and bytes;
- missing, unsupported, unassociated, and stored dispositions;
- included, excluded, pending, and invalid terminal states;
- expected bundle size and minimum local/remote headroom.

Before production mutation, a server-side dry run verifies release/schema compatibility, current production aggregates, bundle/component checksums, versioned-path availability, candidate database name, free disk/memory, and unchanged unrelated workloads. It reports rows that would be new, already identical, or conflicting. Any conflict count greater than zero blocks candidate loading.

### 3. Resumable authenticated transfer

Transfer only immutable bundle components over strict-known-host SSH. Use rsync partial-file retention and whole-transfer progress, resume into an incoming checksum-specific path, then compare local/server size and SHA-256 before extraction or restore. A partially transferred file is never treated as complete, and the incoming path is mode-restricted.

The raw export, extracted source directory, source reports, local database volume, environment files, keys, and provider credentials never cross this boundary.

### 4. Production candidate database

After hotfix PR #67 has produced a healthy schema-`0008` release, E7-T6 should:

1. Acquire the existing WEF deployment lock and re-run non-interference/capacity inventory.
2. Pause WEF writers and terminate only WEF connections to the current production database.
3. Clone the current WEF database to a checksum/version-specific candidate database in the same isolated PostGIS cluster; never clone or connect to another project's database.
4. Resume no writers against the candidate, migrate it forward to the manifest head, and verify that production `users`, `auth_sessions`, and excluded/unrelated state match the maintenance-start snapshot.
5. Restore the bundle into isolated staging tables or an equivalent non-public import boundary, compare canonical row content by primary/unique identity, and fail before merging on any same-key/different-content row.
6. Insert only missing rows in FK-safe bounded batches. Identical rows are unchanged. Batch checkpoints make an interrupted candidate load resumable, but no partially loaded candidate may become active.

The old production database remains intact. The candidate name, connection URL, and credentials stay in mode-restricted release configuration and never enter the manifest or logs.

### 5. Versioned media staging

Extract restricted originals and public derivatives beneath new checksum/version-specific application-owned roots. Validate paths before creation, reject links/special files/path traversal, write through temporary names, set reviewed modes, and verify every file against the logical/object manifest.

Restricted originals are never mounted by the public edge. Public media contains derivatives only. Existing production media roots and current mounts remain untouched. E7-T6 implementation must make candidate media roots explicit release inputs rather than mutating the current shared path in place.

### 6. Non-public candidate verification

Run the candidate release on an internal or loopback-only path with provider egress disabled. Instrumentation and network boundaries must prove:

- zero raw parsing;
- zero hosted geocoder calls;
- zero source-media reads/copies;
- zero derivative transformations;
- exact source/revision/offer/location/geocode/media reconciliation;
- every accepted visible pin and candidate public-media reference resolves;
- restricted originals, source text, contacts, local paths, and credentials remain non-public;
- production identities/sessions and unrelated projects remain unchanged.

Any failed checksum, migration, conflict, load, media, health, privacy, or non-interference gate leaves the current public release and database/media pointers unchanged.

### 7. Activation remains HTTPS-gated

Revision 4 recommends that E7-T6 finish with a verified candidate retained on the production host but not selected by the public release. Public historical-data activation requires E7-T10 and E7-T7 under ADR-019 and should be refined as a separate independently reviewable task after this spike is approved.

The later activation task should briefly pause writers, revalidate candidate freshness or rebuild from the then-current identity/session snapshot, atomically activate a complete release configuration pointing at the candidate database and media roots, run public HTTPS/API/media smokes, and restore the old complete configuration on failure. Same-host retained state is rollback material only and cleanup requires a separate owner authorization.

## Task-boundary recommendation

- Keep E7-T1 through E7-T4 `done` as historical facts.
- Refine and promote [E7-T6 revision 2](proposed-tasks/E7-T6-transfer-and-import-the-historical-dataset.md) after spike approval as bundle creation, resumable transfer, candidate clone/load/media staging, and non-public reconciliation only.
- Keep E7-T8/E7-T9 paused/invalidated until the revision-4 spike and later implementation plan revalidate their place in the sequence.
- Keep E7-T10 proposed behind D-009 and the E7-T8/E7-T9 chain.
- Keep E7-T7 proposed behind its E6 security dependencies and E7-T10.
- During post-spike planning, create a separate historical-candidate activation task depending on staged E7-T6 plus the ADR-019 HTTPS/sensitive-feature gates; do not hide activation inside E7-T6.

## Risks and mitigations

- **Private source rows in the database snapshot:** restrict the bundle/server paths, exclude raw inputs and detailed reports, keep source/contact fields out of APIs/logs, and never publish the database component.
- **Same-host rollback mistaken for backup:** retain old/candidate state but preserve ADR-015 wording; no recovery guarantee exists until E7-T5 is separately approved.
- **Production identity/session drift:** keep activation separate; rebuild or reconcile the candidate from a fresh writer-paused clone before later cutover.
- **Cross-table partial load:** preflight every conflict before merge, load only into an inactive candidate in bounded replay-safe batches, and require full reconciliation before eligibility.
- **Media/DB skew:** manifest object identity and references together; candidate verification rejects any missing, extra, wrong-class, or wrong-hash object.
- **Provider or transformation regression:** disable provider egress/source mounts and instrument invoked commands; any call/read/transform count blocks acceptance.
- **Disk pressure from old, incoming, extracted, candidate, and current state:** compute worst-case headroom before each phase and retain an owner-approved abort threshold.
- **Interference with shared NUC workloads:** inventory exact projects/listeners/resources before/after and target only WEF paths, database names, and Compose resources.
- **Premature HTTP activation:** E7-T6 leaves public pointers unchanged; ADR-019 gates real historical visibility behind E7-T10/E7-T7.

## Invalidation triggers

Return to the spike for a raw-production reimport, direct live restore, whole-database replacement, provider call, regenerated derivative, public activation before ADR-019 gates, cross-project database/shared-edge ownership, cloud/object-storage transfer, or a backup/recovery claim. Return to the later implementation plan for material table scope, bundle format, candidate/load strategy, batch/checkpoint behavior, release inputs, reconciliation gates, transfer path, rollout order, or rollback changes.

## Exit checklist

- [x] E3-T5 source identity, terminal counts, and media counts are recorded only as aggregate/non-sensitive evidence.
- [x] Current production release/schema/counts/capacity and the failed release gate are distinguished as point-in-time observations.
- [x] Raw-export reprocessing, whole-database replacement, and direct live restore are rejected.
- [x] Bundle, dry-run/progress, resumable transfer, candidate clone, conflict behavior, batching, media staging, reconciliation, privacy, and rollback boundaries are explicit.
- [x] ADR-019 is honored: E7-T6 stages but does not publicly activate historical data.
- [x] E7-T8/E7-T9 pause and later revalidation are explicit.
- [x] No production code, executable proof, transfer bundle, private row/media content, or server mutation was created during this spike.
- [x] Owner explicitly approves E7 SPIKE revision 4.

## Owner decision

Flippylolz approved E7 SPIKE revision 4 on 2026-08-15 by reviewing the prepared revision-4 PR, replying `LGTM`, and explicitly directing both prepared PRs to merge. This authorizes proposed-task refinement/promotion and implementation planning only; it does not authorize code, bundle creation, transfer, candidate restore, or production mutation.
