---
schema: ai-workflow/task@1
id: E3-T4
epic: E3
title: "Implement media storage and derivatives"
status: done
revision: 2
priority: P0
size: L
milestone: M2
dependencies: [E2-T3, E3-T1, E3-T2]
requirement_ids: [P-005, P-007]
decision_ids: [ADR-005, ADR-007, ADR-012]
deferred_decision_ids: []
promotion:
  source: ../proposed-tasks/E3-T4-implement-media-storage-and-derivatives.md
  promoted_by: "Cursor Agent (owner-authorized after spike revision 3 approval)"
  promoted_at: "2026-08-14T00:42:00Z"
spike_gate:
  status: satisfied
  file: ../SPIKE.md
  approved_revision: 3
  verified_by: "Cursor Agent"
  verified_at: "2026-08-14T00:42:00Z"
implementation_gate:
  status: satisfied
  file: ../IMPLEMENTATION_PLAN.md
  approved_revision: 3
  verified_by: "Codex (owner-authorized)"
  verified_at: "2026-08-15T06:42:59Z"
dependency_gate:
  status: satisfied
  verified_by: "Codex (owner-authorized)"
  verified_at: "2026-08-15T06:42:59Z"
  evidence:
    - "E2-T3 | done | merged PR https://github.com/Flippylolz/WEF/pull/37"
    - "E3-T1 | done | merged PR https://github.com/Flippylolz/WEF/pull/11"
    - "E3-T2 | done | merged PR https://github.com/Flippylolz/WEF/pull/53 | squash 0016a7a"
branch:
  required: true
  name: feature/E3-T4-media-storage
  task_id: E3-T4
  one_task_only: true
  created_at: "2026-08-15T06:42:59Z"
  pull_request: "https://github.com/Flippylolz/WEF/pull/60"
completion:
  completed_by: "Codex (owner-authorized)"
  completed_at: "2026-08-15T08:00:17Z"
  pull_request: "https://github.com/Flippylolz/WEF/pull/60"
  evidence:
    - "E3-T4 branch feature/E3-T4-media-storage squash-merged via https://github.com/Flippylolz/WEF/pull/60 at 8915d86 after E3-T3 merged; T3 was a review-stack base, not a task dependency"
    - "All four CI jobs passed on the merged head: Backend, Frontend and contract, Repository safety, and Runtime images"
    - "PR verification: 246 backend tests and 33 frontend tests passed; 93.60% backend branch coverage; Ruff, strict mypy, 11 import-linter contracts, contract/runtime/topology/rollback/release/shell/Caddy checks passed"
    - "Acceptance evidence covers pre-read path confinement/no-open rejection, replay-safe restricted originals, storage-class-scoped dedup, source-owned dispositions/associations, metadata-free derivatives, atomic publication, and derivative-only public mounts"
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# E3-T4: Implement media storage and derivatives

> Done through merged [PR #60](https://github.com/Flippylolz/WEF/pull/60) under owner-approved spike and implementation-plan revision 3. E3-T3 was a review-stack base, not a task dependency.

## Outcome

Verify source media and publish replay-safe public derivatives while preserving restricted originals, every source relationship, and explicit reportable outcomes without exposing source or host paths.

## Original roadmap definition

- Priority/size: P0 / L
- Dependencies: E2-T3, E3-T1
- Work:
  - Validate safe source paths/types/sizes.
  - Stream checksums and atomic copies to opaque keys.
  - Generate web thumbnails and metadata.
  - Serve read-only media through the selected edge.
- Acceptance:
  - Traversal, missing, oversized, and unsupported files receive reason codes.
  - Public URLs reveal no source/host path.
  - Checksum deduplication preserves each source relationship.
  - Public derivatives contain no unnecessary EXIF/location metadata.

## Scope

- Add forward migrations/mappings for storage-class-scoped stored objects, source-owned media assets, original media disposition attempts, per-variant derivative attempts, successful versioned derivatives, and ordered offer-media associations.
- Resolve descriptors only beneath the configured read-only source root. Perform descriptor/path confinement, no-follow/symlink, regular-file, supported-type, and safe metadata/size checks before opening content; traversal, symlink, non-regular, missing, oversized-by-metadata, unsupported, and similar failures are recorded without reading unsafe bytes.
- Only after pre-read safety passes, inspect signatures/content, enforce decode/pixel/dimension/duration limits, stream SHA-256, and atomically publish opaque versioned keys.
- Deduplicate physical bytes only within the same storage class while keeping a logical asset for every source message/ordinal and preserving the E2 association rule/confidence. A restricted original and public derivative never share one stored object even when checksums match. `explicit_group` is a first-class stable association rule and must not be collapsed into `same_message`, `manual`, or another fallback.
- Represent every expected media item and association with a disposition: `stored`, `missing`, `rejected`, `unsupported`, or `unassociated`. Every attempt preserves the required non-negative E2 `MediaReference.media_index`/source ordinal even when unassociated, plus the always-resolvable immutable source revision created by T2, descriptor identity, observation status/reason, observed checksum only after safe reading, stable reason, attempt number, verifier/association version, and timestamps.
- Key replay by message, ordinal, immutable source revision, descriptor identity, checksum for safely read content or a stable versioned `unread:<reason>` sentinel, and verifier/association versions. Identical descriptors at different ordinals remain distinct; changed readable bytes create a new attempt, while transition from unread to safely read content cannot reuse a stale unread terminal attempt.
- Separately represent each requested derivative variant attempt as `pending`, `succeeded`, or `failed`, with attempt number, transform version, stable failure reason, source-object checksum, and resulting derivative only on success.
- Keep verified originals in a restricted application-owned originals subtree accessible only to the operator/storage adapter. Generate metadata-free public derivatives into a separate public subtree.
- The API/edge may mount only the public derivative subtree read-only. It must never mount the source tree, restricted originals subtree, or a broad parent containing both.

## Acceptance criteria

- [x] Traversal, absolute, symlink, non-regular, missing, changed, oversized, over-pixel, unsupported, signature/MIME-mismatched, and corrupt inputs receive stable versioned reasons without escaping the source root.
- [x] Traversal, symlink, non-regular, oversized-by-safe-metadata, unsupported-descriptor, missing, and analogous pre-read rejections persist an unread status/sentinel/reason with nullable checksum; tests prove the adapter never opens or hashes those unsafe bytes.
- [x] Missing, rejected, unsupported, and unassociated original outcomes remain queryable with deterministic attempt/reason/version semantics; replay does not erase history or create duplicate terminal attempts.
- [x] Every original attempt retains its non-negative E2 media index, including unassociated outcomes; two identical descriptors at different source ordinals never collapse.
- [x] Every attempt references T2's immutable initial/current source snapshot. Safely readable inputs persist observed checksum; same-descriptor content replacement or an unread input later becoming readable creates a new replay identity and auditable attempt.
- [x] Every derivative variant has independent auditable attempt/status/failure history; a failed thumbnail does not alter the original's stored disposition, and retry/version changes append rather than overwrite.
- [x] Successful writes stream checksums and publish complete bytes atomically to opaque versioned restricted-original/public-derivative keys; interrupted writes expose no partial public file.
- [x] Equal bytes deduplicate physically within `restricted_original` or `public_derivative`, never across those classes; assets reference restricted objects and derivatives reference public objects through tested constraints.
- [x] E2 association rules and confidence survive unchanged, including a tested `explicit_group` association.
- [x] Generated thumbnails are bounded, correctly oriented, transformation-versioned, and free of EXIF/GPS/XMP/comments.
- [x] Public URLs and edge responses reveal no source/host path, use verified content types plus `nosniff`, and can resolve only keys beneath the derivative subtree.
- [x] Tests prove the source and originals mounts are absent from API/edge containers and production runtime layers.
- [x] Disk full, checksum mismatch, replacement race, decode failure, and database failure leave reconciled disposition/history and bounded reportable cleanup.

## Test plan

- Unit: path/key/storage-class/reason/original-disposition/replay-identity/derivative-attempt/version/refcount/variant values, non-negative ordinals, `explicit_group`, association ordering, limits, and idempotency.
- Integration: migration/head, always-resolvable source snapshot references, class-scoped physical/logical uniqueness, class-correct asset/derivative references, identical descriptors at distinct ordinals, same-descriptor content replacement, unread-then-readable replay, original disposition history, derivative failure/retry history, database failure/orphan reporting, and sanitized E2 associations.
- Filesystem/security: generated traversal/symlink/special/missing/oversized-metadata/unsupported pre-read cases with open/read/hash denial assertions, plus race/partial/disk-limit inputs, signature mismatch, corrupt/decompression-bomb-like images, metadata stripping, permissions, and atomic visibility.
- Runtime: operator-only source/original mounts, derivative-only API/edge mounts, no directory listing, no original URL resolution, and production image/build-context exclusions.

## Dependencies and traceability

- Task dependencies: [E2-T3](../../E2-historical-export-parser-audit/tasks/E2-T3-implement-media-grouping.md), [E3-T1](E3-T1-create-schema-and-migrations.md), [E3-T2](E3-T2-implement-idempotent-persistence-and-reprocessing.md)
- E3-T3 is deliberately **not** a task dependency. Sequential delivery may place E3-T3 on `main` first, but geocoding completion/evidence does not gate E3-T4.
- Milestone: [M2](../../../milestones/M2-historical-dataset-ready.md).
- Traceability: [Data model](../../../contracts/DATA_MODEL.md), [Ingestion](../../../ingestion/README.md), [Security](../../../security/README.md), [ADR-007](../../../decisions/adr/ADR-007-mounted-media-storage-interface.md).

## Approval and start boundary

- Spike/implementation gates were satisfied for revision 3, dependencies were complete, and the dedicated E3-T4 branch merged through PR #60.
- Production snapshot transfer/import remains outside this completed task; proposed E7-T6 revision 2 owns materialized database/media delivery.

## Affected modules and contracts

- See the historical approved [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) revision 3 sequence entry for this task and [DATA_MODEL.md](../../../contracts/DATA_MODEL.md).

## Implementation notes

Material departures from the owner-approved plan revision invalidate the affected approval; editing this section alone does not authorize them.

## Rollout and rollback

Follow the task sequence entry in [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md): dedicated branch from then-current `main`, PR targeting `main`, forward-only migrations, schema-compatible rollback only, no destructive data recovery claims.

## Ready checklist

- [x] The file is authoritative under `tasks/`; no duplicate remains under `proposed-tasks/`.
- [x] Promotion source, promoter, and timestamp are recorded.
- [x] `spike_gate` references the owner-approved current spike revision 3 and is `satisfied`.
- [x] `implementation_gate` references the owner-approved current implementation-plan revision containing this task ID/current revision, and is `satisfied`.
- [x] Every dependency is `done` with `dependency_gate: satisfied`, or each incomplete dependency is a valid stacked ancestor; every deferred gate required for start is resolved per the approved plan.
- [x] Scope and acceptance criteria match the approved plan.

## Start checklist

- [x] Status passed through `ready`.
- [x] One new branch contains this task ID.
- [x] The branch contains this task only above its review-stack base; the pull request will be recorded after creation.
- [x] `branch.name` and `branch.created_at` are recorded before setting `in_progress`.

## Done checklist

- [x] Acceptance criteria pass.
- [x] The global [definition of done](../../../workflow/DEFINITION_OF_DONE.md) passes.
- [x] Completion actor, time, pull request, and evidence are recorded.
