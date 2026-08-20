---
schema: ai-workflow/task@1
id: E7-T6
epic: E7
title: "Transfer the verified historical snapshot into a non-public production candidate"
status: in_progress
revision: 3
priority: P1
size: L
milestone: M3
dependencies: [E3-T5, E7-T2, E7-T4]
requirement_ids: [P-001, P-002, P-005, P-007]
decision_ids: [ADR-005, ADR-006, ADR-007, ADR-008, ADR-010, ADR-014, ADR-015, ADR-019]
deferred_decision_ids: []
promotion:
  source: ../proposed-tasks/E7-T6-transfer-and-import-the-historical-dataset.md
  promoted_by: "ZCode agent (owner-directed)"
  promoted_at: "2026-08-16T21:35:12Z"
spike_gate:
  status: satisfied
  file: ../SPIKE.md
  approved_revision: 4
  verified_by: "ZCode agent (owner-directed)"
  verified_at: "2026-08-16T21:35:12Z"
implementation_gate:
  status: satisfied
  file: ../IMPLEMENTATION_PLAN.md
  approved_revision: 4
  verified_by: "ZCode agent (owner-directed)"
  verified_at: "2026-08-16T21:43:56Z"
dependency_gate:
  status: satisfied
  verified_by: "Cursor Agent (autonomous epic mission)"
  verified_at: "2026-08-20T01:30:00Z"
  evidence:
    - "E3-T5 | done | PRs #65/#66"
    - "E7-T2 | done | merged on main"
    - "E7-T4 | done | merged on main"
branch:
  required: true
  name: cursor/feat-e7-t6-transfer-remote-0c74
  task_id: E7-T6
  one_task_only: true
  created_at: "2026-08-20T03:20:00Z"
  pull_request: null
completion:
  completed_by: null
  completed_at: null
  pull_request: null
  evidence:
    - "Slice 1 foundation merged via https://github.com/Flippylolz/WEF/pull/88"
    - "Slice 2 bundle packaging merged via https://github.com/Flippylolz/WEF/pull/89"
    - "Slice 3 candidate config merged via https://github.com/Flippylolz/WEF/pull/90"
    - "Slice 4 transfer remote merged via https://github.com/Flippylolz/WEF/pull/93"
    - "macOS remote path/rsync fix merged via https://github.com/Flippylolz/WEF/pull/95"
    - "Candidate reconcile + loopback compose merged via https://github.com/Flippylolz/WEF/pull/96"
    - "Candidate edge publish network fix merged via https://github.com/Flippylolz/WEF/pull/97"
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# E7-T6: Transfer the verified historical snapshot into a non-public production candidate

> Revision 3 is promoted against approved [spike revision 4](../SPIKE.md). It removes revision 2's activation/cutover tail: this task ends with a completely verified but non-public production candidate. Public historical-data activation is a separate task under the ADR-019 gates.

## Outcome

Transfer the verified E3-T5 terminal database state and application-owned media into a checksum-addressed candidate database and versioned media roots on the supplied NUC, and prove complete reconciliation without re-running parsing, hosted geocoding, manual review, source-media copying, or derivative generation, and without exposing historical data publicly.

## Implementation progress

Cloud-testable repository slices merged on `main` (task remains `in_progress`):

| Slice | PR | Scope |
|-------|-----|-------|
| Foundation | [#88](https://github.com/Flippylolz/WEF/pull/88) | Manifest, dry-run, conflict/checkpoint/path helpers + 11 unit tests |
| Bundle packaging | [#89](https://github.com/Flippylolz/WEF/pull/89) | Source layout, pack/verify, CLI + 5 integration tests |
| Candidate config | [#90](https://github.com/Flippylolz/WEF/pull/90) | Checksum-scoped candidate paths, loopback verification env builder + 5 tests |
| Transfer remote | [#93](https://github.com/Flippylolz/WEF/pull/93) | Transfer plan, rsync command builder, server dry-run gates |
| macOS remote path/rsync fix | [#95](https://github.com/Flippylolz/WEF/pull/95) | Linux remote paths without local resolve; openrsync-compatible rsync-plan |
| Candidate verify | [#96](https://github.com/Flippylolz/WEF/pull/96) | Manifest/media reconcile CLI, loopback `compose.candidate.yaml`, release packaging of transfer tooling |
| Candidate edge publish | [#97](https://github.com/Flippylolz/WEF/pull/97) | Non-internal `verify` network so `127.0.0.1:13100` publishes |

Remaining for full E7-T6 acceptance: formalize staging-table restore/conflict preflight and checkpointed FK-safe load as repository-owned tooling (current candidate load was an operational SSH rehearsal), then record task `done`.

Live production evidence (2026-08-20):

- Bundle rsync verified on NUC; `wef_hist_candidate` holds E3-T5 terminal counts (27,170 messages, 2,999 offers, 792 locations) with 24,532 + 49,059 staged media files.
- `transfer_candidate reconcile` allowed against the incoming bundle; public `wef` remains at 0 source messages / 5 synthetic visible offers.
- Loopback candidate stack `wef-candidate` is healthy on `http://127.0.0.1:13100` (`live`/`ready`); candidate API uses `wef_hist_candidate` with no `provider-egress` network.
- Map APIs both show 5 visible offers because the transferred snapshot keeps 2,994 offers as `needs_review` (only 5 `visible`); historical rows are present in the candidate DB but not public-map-eligible until later activation/review gates.

## Scope

### 1. Immutable local transfer bundle

- Build one ignored, mode-`0600`, checksum-addressed bundle outside every Git/GHCR/Actions/build-context boundary from the completed E3-T5 run only.
- Database component: a selective, data-only PostgreSQL snapshot at migration head `20260815_0008` covering exactly the spike-revision-4 table scope — `locations`, `offers`, `source_channels`, `source_messages`, `source_message_revisions`, `developments`, `offer_sources`, `ingest_runs`, `complete_import_runs`, `provider_daily_budgets`, `provider_attempts`, `geocode_results`, `geocode_miss_claims`, `location_geocode_selections`, `stored_media_objects`, `media_assets`, `media_disposition_attempts`, `media_derivatives`, `media_derivative_attempts`, and `offer_media`.
- Media components: restricted originals and public derivatives archived only from application-owned E3-T5 storage, never from the raw export tree.
- Manifest: non-sensitive records of bundle format, source checksum, pipeline/release/schema identities, terminal aggregate counts, table row counts, media object counts/bytes, and a SHA-256/size/mode for every component and logical media object.
- Terminal-state gate: packaging refuses to start while any import lease is active, any geocode claim is open, any provider work is pending, or any reconciliation/media lineage state is incomplete or mismatched.
- Bundle creation is fail-closed and non-overwriting; re-running with the same inputs reproduces the same logical manifest, and a changed component creates a new bundle identity instead of mutating an existing bundle.

### 2. Dry run, progress, and capacity gates

- Before packaging, display a progress bar and exact counts for selected rows per table, logical/physical media objects and bytes, disposition classes, expected bundle size, and minimum local/remote headroom.
- Before any server mutation, a server-side dry run verifies release/schema compatibility, current production aggregates, bundle/component checksums, versioned-path availability, candidate database name availability, free disk/memory, and unchanged unrelated workloads.
- Both dry runs report rows that would be new, already identical, or conflicting, plus media files/bytes to stage. Any conflict count greater than zero blocks candidate loading.

### 3. Resumable authenticated transfer

- Transfer only immutable bundle components over strict-known-host SSH using resumable `rsync` with partial-file retention and whole-transfer progress into an incoming, checksum-specific, mode-restricted path.
- Compare local/server sizes and SHA-256 checksums before reading or extracting anything; a partially transferred file is never treated as complete.
- The raw export, extracted source directory, source reports, local PostgreSQL volume, environment files, credentials, and provider keys never cross this boundary.

### 4. Production candidate database

- Acquire the existing WEF deployment host lock (`flock` on `$WEF_ROOT/state/deploy.lock`) and re-run the non-interference/capacity inventory before mutating anything.
- Pause only WEF writers and terminate only WEF connections to the current production database.
- Clone the current production WEF database into a checksum/version-specific candidate database in the same isolated PostGIS cluster; never clone or connect to another project's database. Production identities, sessions, and unrelated state are preserved by construction.
- Migrate the candidate forward to the manifest schema head (a verification no-op when production already matches) and verify that production `users`, `auth_sessions`, and excluded/unrelated state match the maintenance-start snapshot.
- Restore through staging tables or an equivalent isolated non-public import boundary; compare canonical row content by primary/unique identity before any merge.
- Preflight all keys: identical rows remain unchanged, missing rows are inserted in FK-safe bounded batches with resumable checkpoints, and any same-key/different-content row aborts before merging. No partially loaded candidate may become active.
- Keep the candidate connection URL and credentials in mode-restricted release configuration only; never in the manifest or logs.

### 5. Versioned media staging

- Extract restricted originals and public derivatives beneath new checksum/version-specific application-owned roots; existing production media roots and mounts remain untouched.
- Validate paths before creation; reject links, special files, and path traversal; write through temporary names; set reviewed modes; verify every file against the logical/object manifest.
- Restricted originals are never mounted by the public edge; public media contains derivatives only.

### 6. Non-public candidate verification

- Run the candidate release on an internal or loopback-only path with provider egress and raw-source mounts disabled.
- Instrumentation and network boundaries must prove zero hosted geocoder calls, zero raw parsing, zero source-media reads/copies, and zero derivative transformations.
- Reconcile all database counts, pins, media references, privacy boundaries, health checks, and unrelated NUC workloads against the E3-T5 terminal aggregates and the maintenance-start inventory.

## Out of scope

- Public historical-data activation, release-pointer switching, and every ADR-019 HTTPS/sensitive-feature gate: proposed [E7-T11](../proposed-tasks/E7-T11-activate-the-verified-historical-candidate.md) owns them after E7-T10 and E7-T7.
- E7-T9/E7-T10 shared-edge work, E7-T7 sensitive features, backups/recovery claims (ADR-015), destructive cleanup of retained old/candidate state, and any provider/parser/transform execution.
- Changes to public API contracts, the persisted application schema (the candidate migrates only to the already-released head), or unrelated NUC projects.

## Affected modules and contracts

- New repository-owned transfer tooling under `scripts/` for bundle creation, dry-run counting, checksummed resumable transfer, candidate clone/restore preflight, bounded batch load, and media staging/verification.
- `scripts/deploy/` release configuration gains explicit candidate database/media-root inputs; the current production release inputs, `compose.production.yaml`, and public contracts do not change.
- No new migrations: the candidate is migrated only to the already-released `20260815_0008` head.

## Implementation notes

- The verified source identity is source checksum `2399a88c70253c3f34b6ab73c423e094e7eb5f179ee9392b87ed715a74c6649d`, pipeline `e3-complete-v2`, schema `20260815_0008`, with 27,170 source messages, 27,171 revisions, 2,994 offers, 792 locations (474 accepted), 665 succeeded and 9 no-result provider attempts, 23,173 stored / 3,952 unassociated / 55 missing / 55 unsupported dispositions, 24,532 restricted originals (2,190,294,326 bytes), and 49,059 public derivatives (5,007,224,426 bytes).
- Re-verify the E3-T5 terminal dry run (everything unchanged, zero pending work) immediately before packaging; a drifted source requires revalidation, not silent rebundling.
- Production observations from 2026-08-16 (release `e8f1a359a438fda003d0655bc573ade6fd26939b`, schema `20260815_0008`, 0 source messages, 5 synthetic offers, 4 locations, 0 users, ~872 GB free disk, ~6.1 GiB available memory) are point-in-time evidence only; recheck every threshold immediately before each mutation.
- Aggregate/identity values may appear in evidence; raw rows, contact values, source-relative paths, local filesystem paths, detailed reports, credentials, and media bytes must never enter Git, GHCR, Actions artifacts, logs, or image layers.
- Same-host retention of the old database/media roots and the candidate is rollback material only; never describe it as backup or recovery while E7-T5 stays deferred.

## Acceptance criteria

- [ ] Packaging refuses any active import lease, open geocode claim, pending provider work, or incomplete reconciliation state, and the bundle identity exactly matches E3-T5's approved source checksum, pipeline/schema versions, terminal counts, selected-review lineage, media dispositions, and object manifest.
- [ ] The bundle stays ignored, mode-`0600`, checksum-addressed, and outside Git/GHCR/Actions/build contexts, containing only the selective data-only snapshot, restricted originals, public derivatives, and the non-sensitive manifest; `users`, `auth_sessions`, `e0_proof_estates`, `alembic_version`, raw export files, source-relative media, detailed reports, credentials, `.env`, provider keys, and the local PostgreSQL volume are excluded and their absence is proven.
- [ ] Dry runs show a progress bar and exact counts for selected rows per table, new/identical/conflicting rows, media files/bytes per class, and expected bundle size/headroom before packaging and again before server mutation.
- [ ] Transfer uses strict-known-host SSH with resumable `rsync`, whole-transfer progress, and partial-file retention; interrupted transfers resume without restarting completed bytes; local/server size and SHA-256 match before anything is read or extracted.
- [ ] The candidate is a clone of the then-current production database under the WEF deployment lock with only WEF writers paused; production `users`, `auth_sessions`, and unrelated state match the maintenance-start snapshot after candidate migration to the bundle head.
- [ ] Restore goes through staging tables or an equivalent isolated boundary; identical rows remain unchanged, missing rows insert in FK-safe bounded batches with resumable checkpoints, and any same-key/different-content row aborts before merge with the candidate left non-active.
- [ ] Media are staged beneath new checksum/version-specific roots with every object verified against the manifest, links/traversal/special files rejected, public roots containing derivatives only, and existing production roots/mounts untouched.
- [ ] The candidate runs non-public with provider egress and raw-source mounts disabled, and instrumentation proves zero hosted geocoder calls, zero raw parsing, zero source-media copies, and zero derivative transformations.
- [ ] Database counts, pins, media references, privacy boundaries, health checks, and unrelated NUC workloads reconcile exactly to the E3-T5 aggregates and the before/after inventories.
- [ ] The production database, media roots, and public release pointers remain unchanged throughout; any failed checksum, migration, conflict, load, media, health, privacy, or non-interference gate leaves the current public release active and retains prior/candidate state for rollback.
- [ ] No historical data becomes publicly visible: the interim HTTP endpoint keeps serving synthetic data only, and the candidate is reachable only through the internal/loopback verification path.

## Test plan

- Unit: manifest generation and reproducibility, terminal-state refusal cases, exclusion rules, conflict classification, path validation, FK-safe batch ordering, and checkpoint resumption logic.
- Integration: local bundle build/verify round trip against fixture data; staging-restore preflight with identical/new/conflicting fixtures; interrupted-transfer resumption with a deliberately partial file; checksum/size mismatch refusal; media staging verification including missing, extra, wrong-class, and wrong-hash objects.
- End-to-end: full local rehearsal of bundle → verified transfer → candidate clone/load → media staging → non-public reconciliation with provider egress disabled, plus the recorded production runbook execution.
- Security/operations: secret and private-data exclusion scans of bundle/manifest/logs, mode checks, privacy-boundary probes, capacity-gate and lock/writer-pause behavior, and exact before/after non-interference inventory comparison.

## Rollout and rollback

Execution order: terminal-state check → bundle → local verification → transfer → server verification → lock + writer pause → clone → migrate → staging restore/preflight → bounded load → media staging → non-public candidate verification → writer resume with production pointers unchanged. Rollback at any point is abandoning or retaining the candidate and re-checking the unchanged public release; no destructive cleanup occurs without a separate owner authorization. Same-host retention is rollback material, not a backup.

## Ready checklist

- [x] The file is authoritative under `tasks/`; no duplicate remains under `proposed-tasks/`.
- [x] Promotion source, promoter, and timestamp are recorded.
- [x] `spike_gate` references owner-approved spike revision 4 and is `satisfied`.
- [x] `implementation_gate` references the owner-approved implementation-plan revision 4 (approved 2026-08-16, containing E7-T6 revision 3) and is `satisfied`.
- [x] Every dependency is `done` with `dependency_gate: satisfied`.
- [ ] Scope and acceptance criteria match the approved plan.

## Start checklist

- [ ] Status passed through `ready`.
- [ ] One new branch contains this task ID.
- [ ] The branch and pull request contain this task only.
- [ ] `branch.name` and `branch.created_at` are recorded before setting `in_progress`.

## Done checklist

- [ ] Acceptance criteria pass.
- [ ] The global [definition of done](../../../workflow/DEFINITION_OF_DONE.md) passes.
- [ ] Completion actor, time, pull request, and evidence are recorded.
