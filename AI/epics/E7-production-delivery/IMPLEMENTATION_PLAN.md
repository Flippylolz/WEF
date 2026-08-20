---
schema: ai-workflow/implementation-plan@1
epic: E7
title: "Docker/GitHub production delivery implementation plan"
status: approved
revision: 5
owner: owner
spike_revision: 4
task_sequence:
  - id: E7-T9
    revision: 1
approval:
  required_role: owner
  status: approved
  decided_by: Flippylolz
  decided_at: "2026-08-20T10:00:00Z"
  approved_revision: 5
  evidence: "Owner continue directive after E7-T6 completion; proposed revision 5 merged through feat/e7-t9-cutover-slice1"
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# Implementation Plan: Reversible shared-edge cutover automation

> Revision 5 authorizes only E7-T9 revision 1 after E7-T6 completion. Revision 4 remains the historical approval for the completed transfer task.

## Approved spike baseline

- [Spike revision 4](SPIKE.md) remains current. E7-T6 is `done`; the owner pause on E7-T9 is satisfied.
- E7-T1 through E7-T4, E7-T6, and E7-T8 are `done`. E7-T5 stays deferred, E7-T7/E7-T10/E7-T11 stay proposed behind their gates.
- D-009 still gates only E7-T10 live rollout.

## Scope and outcome

Deliver locally proven, host-safe automation that can move WEF and AI Forecast behind the isolated shared edge in independently verified stages and restore the previous validated configuration/listeners on failure. Repository changes only; server execution belongs to E7-T10 after D-009 resolution.

## Ordered task sequence

### 1. E7-T9 — Implement reversible shared-edge cutover

- Task: [E7-T9 revision 1](tasks/E7-T9-implement-reversible-shared-edge-cutover.md).
- Dependencies: E7-T8 `done`.
- Affected modules/contracts: cutover compose overlay, `scripts/deploy/shared_edge_*` preflight/inventory/activate/smoke/rollback helpers; existing Caddy `:3100` rehearsal remains rollback material.
- Tests: unit/static gates, fixture integration proofs, production topology proof extensions, forbidden-command scans.
- Rollout: inert automation only; revert the dedicated PR to roll back repository changes.

## Cross-task architecture

- WEF cleanup must not remove the external edge network; edge cleanup must not run WEF or AI Forecast Compose commands.
- AI Forecast routing uses only its retained host `:3000` listener through explicit Linux host-gateway mapping.
- Never switch current pointers or redirects until config validation and both upstream health checks pass.

## Invalidation triggers

Return to the spike for live DNS/ACME, public listener mutation, or cross-project ownership changes. Return to this plan for material cutover stage or rollback boundary changes.

## Owner decision

Flippylolz authorized resumption through the 2026-08-20 continue directive after E7-T6 completion. Revision 5 authorizes E7-T9 revision 1 only; E7-T10, E7-T7, and E7-T11 remain outside this approval.

## Historical note: revision 4 (E7-T6, complete)

The sections below record the completed E7-T6 approval baseline for audit only.

## Approved spike baseline (revision 4)

- [Spike revision 4](SPIKE.md) was explicitly approved by Flippylolz on 2026-08-15 (revision-4 PR review, `LGTM`, and merge direction). It selects the verified E3-T5 materialized-snapshot transfer with an immutable selective bundle, resumable checksummed transfer, a cloned production candidate database, versioned media roots, and complete non-public reconciliation.
- Binding spike constraints: never transfer the raw export, source-relative media, detailed reports, credentials, `.env`, provider keys, or the local PostgreSQL volume; make zero hosted provider calls, zero parsing, zero source-media copies, and zero derivative transformations; abort on any same-key/different-content conflict; leave production identities/sessions and unrelated NUC workloads unchanged; keep the result non-public under ADR-019.
- Historical facts preserved: E7-T1 through E7-T4 and E7-T8 are `done`. E7-T9 remains paused/invalidated pending separate owner revalidation and is absent from this sequence. E7-T5 stays deferred, E7-T7 and E7-T10 stay proposed, and the new activation task [E7-T11](proposed-tasks/E7-T11-activate-the-verified-historical-candidate.md) stays proposed behind the ADR-019 gates.
- Point-in-time production observations from 2026-08-16: release `e8f1a359a438fda003d0655bc573ade6fd26939b`, schema `20260815_0008`, 0 source messages, 5 synthetic offers, 4 locations, 0 users, ~872 GB free disk, ~6.1 GiB available memory. The hotfix-#67 prerequisite from the spike is satisfied (schema head reached and a healthy release deployed), but every value must be rechecked immediately before each mutation.

## Scope and outcome

Deliver the E7-T6 result: the verified E3-T5 terminal state transferred into a checksum-addressed, completely reconciled, non-public production candidate database plus versioned media roots on the supplied NUC, with bundle creation, dry-run/capacity gates, resumable transfer, candidate clone/load, media staging, and non-public verification — and with the public release, database, and media pointers unchanged. Public activation is explicitly excluded and belongs to proposed E7-T11 after E7-T10 and E7-T7.

## Ordered task sequence

### 1. E7-T6 — Transfer the verified historical snapshot into a non-public production candidate

- Task: [E7-T6 revision 3](tasks/E7-T6-transfer-and-import-the-historical-dataset.md).
- Independently reviewable: one coherent tooling plus operations change with its own acceptance, evidence, and rollback boundary; it produces no public behavior change.
- Dependencies: E7-T2 and E7-T4 are `done` (server baseline; release/rollback machinery). E3-T5's implementation PRs #65/#66 are merged with a terminal dry run, but its completion record is still pending; E7-T6 may move to `ready` only after E3-T5 records `done`. No stacking shortcut is available because PR #65 is already merged.
- Affected modules/contracts: new transfer tooling under `scripts/`; `scripts/deploy/` release configuration gains explicit candidate database/media-root inputs. No public API, persisted schema (candidate migrates only to released head `20260815_0008`), or current production release changes.
- Tests: unit refusal/classification logic, fixture-based bundle/restore/transfer-interruption integration proofs, local end-to-end rehearsal with egress disabled, secret/private-data exclusion scans, and before/after non-interference inventory comparison.
- Risks, rollout, and rollback: summarized below and in the task; candidate-only mutation with production pointers unchanged.

## Cross-task architecture

- E7-T6 consumes the E3-T5 materialized state read-only: the local pipeline is never re-run, so the E3 ingestion core (ADR-006) and provider stack are untouched in production.
- The candidate database is created by cloning the current production database inside the existing isolated PostGIS cluster (ADR-005); the bundle's data-only component is restored through staging tables, compared by canonical identity, and merged only as missing-row inserts.
- Candidate database URL/media roots become explicit, mode-restricted release configuration inputs owned by the deployment tooling (ADR-008/ADR-014); the ordinary deploy workflow and `compose.production.yaml` keep their current inputs until a later approved activation task switches them.
- E7-T11 (proposed) is the only consumer of the verified candidate; E7-T6 hands it a freshness-revalidation or rebuild contract rather than an implicitly trusted snapshot.

## Data and migrations

- No application schema changes and no new Alembic revisions: the candidate is migrated only forward to the already-released bundle head `20260815_0008`, which today matches production (a verified no-op that must still be proven, and must handle a lagging production clone if state drifts).
- Bundle table scope is exactly the spike-revision-4 list of catalog/ingestion tables; `users`, `auth_sessions`, `e0_proof_estates`, and `alembic_version` are excluded, and their equality to the maintenance-start snapshot is verified after clone/migration.
- Loading is idempotent and replay-safe: identical rows unchanged, missing rows inserted in FK-safe bounded batches with checkpoints, and any same-key/different-content row aborts before merge. An interrupted load resumes from checkpoints; a partially loaded candidate never becomes active.
- The production database and current media roots are never written; they are retained unchanged as rollback material. Same-host retention is not a backup (ADR-015); no recovery guarantee is claimed and cleanup requires separate owner authorization.

## Security and privacy

- The bundle is ignored, mode-`0600`, checksum-addressed, and never enters Git, GHCR, Actions artifacts, logs, or image layers; static exclusion tests must fail on credentials, `.env`, provider keys, raw export paths, and detailed reports.
- The manifest is non-sensitive by construction: identities, aggregate counts, sizes, and SHA-256 values only — no contact values, raw rows, or local/source-relative paths.
- Candidate execution runs on an internal/loopback-only path with provider egress and raw-source mounts disabled; instrumentation must prove zero hosted geocoder calls, zero parsing, zero source-media copies, and zero derivative transformations.
- Restricted originals stay non-public and unmounted by the edge; public candidate media contains derivatives only; source text and contacts stay out of APIs and logs.
- Transfer uses strict-known-host SSH; the candidate connection URL/credentials live only in mode-restricted release configuration.

## Test and verification strategy

- Repository: markdown links, format/lint/type/tests/contracts, shell syntax/shellcheck for new scripts, and secret/source/image exclusion audits.
- Bundle: terminal-state refusal cases (active lease, open claim, pending provider work, incomplete reconciliation), exclusion completeness, manifest reproducibility, and fail-closed non-overwriting creation.
- Transfer: resumption from a deliberately partial file, whole-transfer progress reporting, and size/SHA-256 verification refusal on mismatch before any read/extraction.
- Candidate load: staging-boundary preflight with identical/new/conflicting fixtures, FK-safe bounded batches, checkpoint resume, and abort-before-merge on conflict.
- Media staging: manifest verification of every object, rejection of links/traversal/special files, derivative-only public roots, and untouched existing roots/mounts.
- Verification: reconciliation against E3-T5 aggregates, visible-pin and media-reference resolution, privacy-boundary probes, health checks, and exact before/after non-interference inventory of NUC projects/listeners/resources.

## Operations, rollout, and rollback

- Configuration ownership: GitHub Actions variables/secrets remain the deploy-configuration owner; candidate inputs are additional release configuration transferred through the existing validated, atomic path — never hand-edited on the host.
- Execution order: terminal-state check → bundle → local verification → transfer → server verification → deployment lock + WEF-writer pause → clone → migrate → staging restore/preflight → bounded load → media staging → non-public candidate verification → writer resume with production pointers unchanged.
- Capacity gates run before every phase; worst-case disk accounting includes old, incoming, extracted, candidate, and current state with an owner-approved abort threshold.
- Rollback: any failed gate abandons or retains the candidate and re-verifies the unchanged public release; no destructive cleanup without separate owner authorization. Retained state is rollback material only, not a backup claim.

## Risks and mitigations

- **Private source rows in the database snapshot:** restricted bundle/server paths, excluded raw inputs/reports, static exclusion tests, and never publishing the database component. (E7-T6)
- **Cross-table partial load:** preflight every conflict before merge, bounded replay-safe batches with checkpoints, and full reconciliation before the candidate counts as verified. (E7-T6)
- **Media/database skew:** manifest identity binds rows and objects together; verification rejects any missing, extra, wrong-class, or wrong-hash object. (E7-T6)
- **Provider or transformation regression:** egress disabled, source mounts absent, and instrumented command boundaries where any call/read/transform count blocks acceptance. (E7-T6)
- **Production identity/session drift:** clone-paused writers, post-clone snapshot equality checks, and activation-time freshness revalidation owned by E7-T11. (E7-T6, E7-T11)
- **Disk/memory pressure on the shared NUC:** phase-gated worst-case headroom checks with abort thresholds and rechecked point-in-time observations. (E7-T6)
- **Interference with unrelated workloads:** exact before/after project/container/network/volume/listener inventory and WEF-only targeting of paths, database names, and Compose resources. (E7-T6)
- **Premature activation:** E7-T6 leaves all public pointers unchanged; ADR-019 gates historical visibility behind E7-T10/E7-T7 and a separate E7-T11 approval. (E7-T6, E7-T11)

## Invalidation triggers

Return to the spike for a raw-production reimport, direct live-database restore, whole-database replacement, hosted provider call, regenerated derivative, public activation before the ADR-019 gates, cross-project database/shared-edge ownership, cloud/object-storage transfer, or any backup/recovery claim. Return to this plan for material changes to table scope, bundle format, candidate/load strategy, batch/checkpoint behavior, release inputs, reconciliation gates, transfer path, task order, or rollback boundaries, or if E3-T5's verified snapshot identity materially changes before transfer.

## Approval checklist

- [x] The referenced spike revision 4 has explicit owner approval and remains valid.
- [x] Every sequence entry is a promoted task with complete acceptance criteria and traceability (E7-T6 revision 3, promoted in the same change).
- [x] Dependencies are complete and acyclic: E7-T2/E7-T4 are `done`; E3-T5 must record `done` before E7-T6 reaches `ready`, and its gate stays `blocked` until then.
- [x] Affected modules, contracts, tests, migrations (none new), risks, rollout, and rollback are explicit.
- [x] Deferred decisions required for implementation are resolved (D-002 is not a gate because no provider call is made; D-009 gates only E7-T10).
- [x] No production or disposable proof code has been written for this scope.
- [x] `revision` 4 represents the material plan being submitted.
- [x] `revision` 4 was submitted as `awaiting_approval` with approval `pending`, then explicitly owner-approved on 2026-08-16 and recorded as `approved` for this same revision.

## Owner decision

Flippylolz explicitly approved E7 IMPLEMENTATION_PLAN revision 4 by name on 2026-08-16 in the owner-directed ZCode session; the decision is recorded in the YAML `approval` object above. It authorizes only E7-T6 revision 3 as sequenced here; E7-T6 must still satisfy its dependency gate (E3-T5 `done`), pass through `ready` on its dedicated branch, and complete the definition of done. E7-T9 revalidation, E7-T10, E7-T7, and E7-T11 remain outside this approval.
