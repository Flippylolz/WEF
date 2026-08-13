---
schema: ai-workflow/implementation-plan@1
epic: E2
title: "Historical export parser and audit implementation plan"
status: awaiting_approval
revision: 2
owner: owner
spike_revision: 2
task_sequence:
  - id: E2-T1
    revision: 2
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

# Implementation Plan: Historical export parser and audit

## Approved spike baseline

[E2 spike revision 2](SPIKE.md) approves a constant-memory Telegram Desktop source adapter, stable framework-independent `RawMessage` boundary, deterministic source/per-record checksums, reconciled input classification, and source-derived but irreversibly sanitized fixture corpus.

It does not approve candidate/extractor rules, media grouping, persisted dry-run reports, a complete export audit/import, database/API changes, live Telegram access, or replacement of the persisted synthetic M1 map seed.

## Scope and outcome

Deliver only [E2-T1 revision 2](tasks/E2-T1-implement-source-adapter-and-fixture-corpus.md): a bounded historical export adapter and safe real-shape corpus that later E2 tasks consume without source-specific logic crossing the `RawMessage` boundary.

The result advances the epic outcome—deterministic extraction from the raw Telegram export with reconciled dry-run reporting—without yet detecting listings, deriving fields, grouping galleries, writing reports, or persisting data.

## Ordered task sequence

### 1. E2-T1 — Implement source adapter and fixture corpus

- Task: [E2-T1 revision 2](tasks/E2-T1-implement-source-adapter-and-fixture-corpus.md).
- Dependency: E1-T2 is `done` through merged [PR #7](https://github.com/Flippylolz/WEF/pull/7).
- Independent result: framework-independent source contract plus iJSON historical adapter and reviewed fixture/golden corpus.
- Verification: bounded-reader and generated-large-input tests, fixture goldens/safety scans, malformed/truncated/channel failures, actual ignored export metadata/count/checksum scan, import boundaries, full repository CI.

E2-T2 through E2-T5 remain under `proposed-tasks/` and are not executable sequence entries.

## Architecture and dependency direction

- `features.ingestion.domain` owns immutable raw-message, source metadata, media descriptor, classification, reason-code, checksum, and count values.
- `features.ingestion.application` owns the historical source port and complete/partial scan lifecycle/result contracts.
- `features.ingestion.infrastructure` implements the port with `ijson`; iJSON types/exceptions do not cross into application/domain.
- Infrastructure depends inward. Domain/application must not import FastAPI, Pydantic, SQLAlchemy, settings, or iJSON; extend `.importlinter` to enforce that boundary.
- Add current iJSON through `uv`; commit the generated `uv.lock` change. Do not add Typer, Telethon, phonenumbers, persistence, or another parser dependency in E2-T1.
- Composition/API/operator wiring is not required. A local acceptance invocation may construct the adapter directly and must emit only non-sensitive aggregate evidence.

## Source and checksum behavior

- Open the configured file in binary mode. A bounded preflight validates top-level keys and expected channel metadata; a bounded full pass iterates `messages.item`.
- No `json.load`, `Path.read_text`, unbounded `read`, or tuple/list collection of all records is permitted.
- A hash-tracking reader computes the byte-exact export SHA-256 during a complete pass. A stopped/failed pass remains explicitly incomplete and cannot expose a successful final summary.
- Per-record SHA-256 uses canonical compact UTF-8 JSON with sorted keys and `ensure_ascii=False`; this is intentionally distinct from unavailable original per-object byte spans.
- `date_unixtime` and `edited_unixtime` create timezone-aware UTC values. Original date strings remain in the raw payload.
- Mixed text flattening preserves segment order and Unicode exactly; original text and entity values remain internal evidence.
- Every input item produces one typed result and one primary count. Reply/mixed-text flags are supplemental. Missing/invalid record fields are malformed results; unknown but valid values are preserved/unhandled; invalid/truncated source JSON or channel mismatch fails closed.

## Fixture and data-safety boundary

- Commit fixtures only below `apps/backend/tests/fixtures/telegram_export/`; never reference the ignored source through a test path.
- Source-derived cases are manually reviewed and irreversibly sanitized: rebase channel/message/reply IDs and dates, replace source/channel/agent/contact identity, generalize addresses and values, replace media paths, and omit media bytes.
- Preserve only the real Unicode, whitespace, mixed entity/link, service/photo/video/reply/empty descriptor structure needed by the adapter contract.
- Add synthetic structurally malformed and truncated documents rather than copying malformed private payload.
- Golden outputs are generated from the sanitized bytes and include `RawMessage`, result kind/reason, canonical record checksum, source metadata, and reconciled counters.
- A safety test rejects broad phone/mention patterns, the real channel ID/name/username, absolute/traversal paths, archive/media/session/key extensions, and binary files.
- The real 21 MB export is used only for a local read-only acceptance scan. Its payload and samples never enter Git, terminal output, logs, CI, reports, or images.

## Contracts, persistence, and compatibility

- No migration or database transaction.
- No public HTTP/OpenAPI/frontend contract change.
- No canonical `SourceMessage`, `Offer`, location, contact, geocode, media, or `IngestRun` write.
- `RawMessage` is an internal replay boundary for later historical/live adapters. A material field/identity/checksum/timestamp semantic change invalidates the spike.
- Unknown source fields remain in the internal raw payload so additive Telegram export changes do not silently disappear.

## Test and verification strategy

- Unit: value validation, UTC timestamps, text flattening, canonical checksum/key-order invariance, classification, counters, and stable malformed reasons.
- Golden adapter: string/mixed text, typed link/entity, service, photo, video/thumbnail, reply, empty caption, unknown field/type, and exact source metadata.
- Failure: missing IDs/timestamps, wrong top-level/channel metadata, truncated/invalid JSON, source I/O error, and partial summary access.
- Bounded processing: guarded reader rejects negative/unbounded reads and records maximum chunk size; generated large input proves the adapter does not retain all records.
- Safety: fixture leak scanner plus Git/Docker/runtime source exclusions.
- Local acceptance: complete ignored export scan must report 21,634,277 bytes, approved SHA-256, 27,082 total records, 27,075 message/7 service, 23,834 string/3,248 mixed text, 26,991 photo, 78 file/video, 11 reply, and terminal success without payload output.
- Repository: frozen install, Ruff format/lint, strict mypy, import-linter (including deliberate forbidden import proof), pytest with branch coverage, dependency audit, OpenAPI/TypeScript drift checks, production builds, and repository safety.

## Rollout and rollback

E2-T1 is inert library/test code and a dependency lock update. It does not activate an importer, database write, network call, or production path. Revert its commit/PR to roll back; no migration, data restoration, media cleanup, or deployment ordering is required.

The feature branch must be created from the latest `main` only after this exact plan revision is separately owner-approved and E2-T1's implementation gate is satisfied. Open one E2-T1 PR, record acceptance evidence in that task, rerun CI after the evidence commit, and merge only when all required jobs are successful.

## Risks and mitigations

- **Fixture privacy leak:** irreversible manual sanitization plus broad automated fixture/source-identity scans; no random slice or generation that defaults to raw output.
- **False bounded-memory claim:** guarded-reader and generated-large-input tests; actual local scan; no full-record collection API.
- **Checksum ambiguity:** byte-exact export hash and separately documented canonical per-record hash.
- **Partial scan mislabeled complete:** explicit lifecycle state; final checksum/reconciliation inaccessible until exhaustion.
- **Schema drift silently omitted:** preserve unknown payload fields, type valid unknowns as unhandled, and fail closed on top-level/channel mismatch.
- **Scope creep into parsing/reporting/persistence:** no candidate rules, grouping, report CLI, database/API/map-seed mutation, or media access.

## Invalidation triggers

Return to the spike for a changed `RawMessage` identity/field contract, checksum meaning, timestamp authority, source privacy model, channel validation policy, shared historical/live boundary, or a different parser/dependency architecture. Return to this plan for material module boundaries, fixture policy/cases, classification/count semantics, test strategy, task scope, dependency, rollout, or rollback changes.

## Approval checklist

- [x] E2 spike revision 2 has explicit owner approval and remains current.
- [x] E2-T1 revision 2 is promoted with complete acceptance criteria and traceability.
- [x] E1-T2 is `done`; the sequence is complete, acyclic, and enforceable.
- [x] Modules, dependency direction, contracts, fixtures, tests, risks, rollout, and rollback are explicit.
- [x] E2-T1 has no deferred decision or migration.
- [x] E2-T2 through E2-T5 remain proposed and absent from the executable sequence.
- [x] No production or test code was written before this approval request.
- [x] Revision 2 is `awaiting_approval` with `approval.status: pending`.

## Owner decision

Implementation-plan revision 2 awaits a separate explicit owner decision. The current spike-only approval does not approve this plan. Until approval metadata records revision 2, E2-T1 remains `draft`, its implementation gate remains blocked, and no feature branch or production/test code is authorized.
