---
schema: ai-workflow/task@1
id: E2-T1
epic: E2
title: "Implement source adapter and fixture corpus"
status: ready
revision: 2
priority: P0
size: M
milestone: M1
dependencies: [E1-T2]
requirement_ids: [P-006, P-007]
decision_ids: [ADR-006, ADR-012]
deferred_decision_ids: []
promotion:
  source: ../proposed-tasks/E2-T1-implement-source-adapter-and-fixture-corpus.md
  promoted_by: "Cursor Agent (owner-authorized)"
  promoted_at: "2026-08-13T18:00:00Z"
spike_gate:
  status: satisfied
  file: ../SPIKE.md
  approved_revision: 2
  verified_by: "Cursor Agent"
  verified_at: "2026-08-13T18:00:00Z"
implementation_gate:
  status: satisfied
  file: ../IMPLEMENTATION_PLAN.md
  approved_revision: 2
  verified_by: "Cursor Agent"
  verified_at: "2026-08-13T18:20:00Z"
dependency_gate:
  status: satisfied
  verified_by: "Cursor Agent"
  verified_at: "2026-08-13T18:00:00Z"
  evidence:
    - "E1-T2 | done | merged PR https://github.com/Flippylolz/WEF/pull/7 | merge 07ee778"
branch:
  required: true
  name: null
  task_id: E2-T1
  one_task_only: true
  created_at: null
  pull_request: null
completion:
  completed_by: null
  completed_at: null
  pull_request: null
  evidence: []
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# E2-T1: Implement source adapter and fixture corpus

> Promoted after explicit owner approval of E2 spike revision 2. Implementation-plan revision 2 is now owner-approved, every task gate is satisfied, and E2-T1 is ready to start on its dedicated branch.

## Outcome

Provide the bounded Telegram Desktop export adapter and reviewed real-shape fixture corpus that later E2 tasks can consume through one stable, framework-independent `RawMessage` boundary.

## Scope

- Add an ingestion feature with framework-independent raw-message, media-descriptor, adapter-result, classification, count, and source-metadata values.
- Add a Telegram Desktop JSON infrastructure adapter using `ijson` over binary input without materializing the document or `messages` array.
- Preflight top-level/channel metadata, calculate the exact export SHA-256, and calculate deterministic canonical JSON checksums for every record.
- Convert Unix timestamp fields to timezone-aware UTC while preserving source date strings in the raw payload.
- Flatten string and mixed Telegram text in order while retaining the original text representation and typed entities.
- Emit one accepted, unhandled, or malformed result for every input record and reconcile exactly one primary classification per record.
- Commit a small source-derived, irreversibly sanitized fixture corpus plus synthetic malformed/truncated cases and golden outputs.
- Add automated fixture-safety checks for contact-like content, source identity, unsafe paths, and media/binary leakage.

## Out of scope

- Candidate detection or typed real-estate field extraction (E2-T2).
- Reply/time-burst media grouping (E2-T3).
- Persisted dry-run reports, final reconciliation reports, or operator reporting CLI (E2-T4).
- Full-export audit/acceptance publication (E2-T5).
- Source/canonical database writes, migrations, geocoding, media file access/copy, API changes, live Telegram/Telethon, or replacing the persisted synthetic M1 map seed.

## Affected modules and contracts

- `apps/backend/src/wef_backend/features/ingestion/domain/`
- `apps/backend/src/wef_backend/features/ingestion/application/`
- `apps/backend/src/wef_backend/features/ingestion/infrastructure/`
- `apps/backend/tests/fixtures/telegram_export/`
- Backend dependency lock and import-linter contracts.
- [Ingestion pipeline](../../../ingestion/PIPELINE.md), [data quality](../../../data/QUALITY_AND_READINESS.md), [data model](../../../contracts/DATA_MODEL.md), and [ADR-006](../../../decisions/adr/ADR-006-shared-ingestion-core.md).

No public HTTP or persisted database contract changes in E2-T1.

## Implementation notes

- Use `ijson.items(binary_file, "messages.item")`; bounded preflight and scan passes may reopen the file but may never call `json.load`, `Path.read_text`, or an unbounded read.
- The exact export checksum covers source bytes. Per-record checksums cover canonical compact UTF-8 JSON with sorted keys and preserved Unicode.
- `date_unixtime` and `edited_unixtime` are authoritative for UTC instants. Original `date`/`edited` strings remain raw evidence.
- Mixed text concatenates string segments and each object segment's `text` without normalization; original mixed text and `text_entities` remain available internally.
- Primary reconciliation kinds are `service`, `photo`, `video`, `text`, `empty`, `unhandled`, and `malformed`. Reply and mixed-text counters are orthogonal.
- Missing/invalid required record fields produce a typed malformed result with stable reason code, source index, and checksum. Invalid/truncated documents and channel mismatch fail the source scan with redacted errors.
- A partial consumer cannot obtain or claim a complete checksum/reconciliation summary.
- Domain/application code must remain independent of iJSON, FastAPI, Pydantic, SQLAlchemy, and settings. The iJSON dependency remains in infrastructure.

## Acceptance criteria

- [ ] The ignored 21,634,277-byte export streams to completion with SHA-256 `d349e27003058f470fa53e5cd9004fe6759e8db466bc690f132398e038816249` and 27,082 reconciled records without whole-file loading.
- [ ] Every input item produces exactly one primary accepted/unhandled/malformed result; primary counts sum to total records and partial scans cannot report completion.
- [ ] `RawMessage` preserves channel/message/reply identity, UTC timestamps, type, flattened and original text/entities, media descriptors, raw payload, and deterministic checksum.
- [ ] Tests cover string/mixed text, service, photo, video/thumbnail, reply, empty caption, unknown fields/type, structurally malformed record, truncated JSON, and channel mismatch.
- [ ] Export and per-record checksum behavior is deterministic, and equivalent source data does not depend on locale, process timezone, or JSON key order.
- [ ] The committed source-derived fixtures contain no real channel identity, message IDs, contacts, agent names, identifying address, unsafe media path, source payload slice, or media bytes.
- [ ] Import-linter and tests prove the ingestion core is framework-independent and iJSON remains an infrastructure concern.
- [ ] E2-T1 performs no database/API/map-seed mutation and does not implement E2-T2 through E2-T5 behavior.

## Test plan

- Unit: value validation, UTC conversion, canonical checksum, text flattening, classification, counters, and malformed reason codes.
- Adapter/golden: stream each sanitized fixture and compare complete `RawMessage`/result/count output.
- Failure: truncated/invalid JSON, wrong channel, missing required fields, unknown types, unsafe partial-summary access.
- Bounded I/O: a guarded reader rejects unbounded reads and records the maximum requested chunk; a generated large fixture proves memory use does not scale with record count.
- Fixture safety: scan all committed fixture bytes/names for forbidden identity/contact/path/media patterns.
- Local source acceptance: scan the ignored 21 MB export and emit only checksum, metadata, shape counts, and terminal status.
- Repository: Ruff format/lint, strict mypy, import-linter, pytest with branch coverage, dependency audit, contract checks, and runtime image/source exclusions.

## Rollout and rollback

The adapter is inert library code with no persistence or network side effect. Before merge, discard the task branch. After merge, revert the E2-T1 commit and dependency lock change; no data rollback or migration is required. A contract/ingestion-semantics departure returns to the spike gate, while a material module/test/fixture change returns to the implementation-plan gate.

## Ready checklist

- [x] This file is authoritative under `tasks/`; the proposed source is removed.
- [x] Promotion source, promoter, and timestamp are recorded.
- [x] `spike_gate` references owner-approved E2 spike revision 2 and is `satisfied`.
- [x] `implementation_gate` references owner-approved implementation-plan revision 2 and is `satisfied`.
- [x] E1-T2 is `done` and recorded by the satisfied dependency gate.
- [x] Scope and acceptance criteria match approved spike revision 2.

## Start checklist

- [ ] Status passes through `ready`.
- [ ] Dedicated branch `feature/E2-T1-telegram-export-adapter` is created from the latest `main`.
- [ ] Branch/PR contain E2-T1 only and branch metadata is recorded before `in_progress`.

## Done checklist

- [ ] Acceptance criteria pass.
- [ ] The global [definition of done](../../../workflow/DEFINITION_OF_DONE.md) passes.
- [ ] Completion actor, time, pull request, and evidence are recorded.
