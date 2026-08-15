---
schema: ai-workflow/task@1
id: E3-T2
epic: E3
title: "Implement idempotent persistence and reprocessing"
status: done
revision: 2
priority: P0
size: L
milestone: M1
dependencies: [E2-T2, E3-T1]
requirement_ids: [P-002, P-006, P-007]
decision_ids: [ADR-003, ADR-005, ADR-006, ADR-012]
deferred_decision_ids: []
promotion:
  source: ../proposed-tasks/E3-T2-implement-idempotent-persistence-and-reprocessing.md
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
  verified_by: "ZCode Agent"
  verified_at: "2026-08-15T03:52:26Z"
dependency_gate:
  status: satisfied
  verified_by: "Cursor Agent (owner-authorized promotion)"
  verified_at: "2026-08-14T00:42:00Z"
  evidence:
    - "E2-T2 | done | merged PR https://github.com/Flippylolz/WEF/pull/36"
    - "E3-T1 | done | merged PR https://github.com/Flippylolz/WEF/pull/11"
branch:
  required: true
  name: feature/E3-T2-idempotent-persistence
  task_id: E3-T2
  one_task_only: true
  created_at: "2026-08-15T03:52:26Z"
  pull_request: "https://github.com/Flippylolz/WEF/pull/53"
completion:
  completed_by: "ZCode Agent (owner-authorized)"
  completed_at: "2026-08-15T04:31:23Z"
  pull_request: "https://github.com/Flippylolz/WEF/pull/53"
  evidence:
    - "E3-T2 branch feature/E3-T2-idempotent-persistence squash-merged via https://github.com/Flippylolz/WEF/pull/53 (squash 0016a7a, branch deleted); one task per branch/PR"
    - "Acceptance: migration 20260815_0004 upgrades clean schemas to head with repeated upgrade a no-op; revision 1 created on initial ingestion, unchanged replay creates none, changed checksum appends exactly one ordered snapshot and atomically advances the current pointer; current checksum/text/payload equals the referenced snapshot (integration assertions)"
    - "Every accepted candidate carries an exact primary OfferSource relationship with deterministic contact-free extraction_json bound to the immutable revision; non-candidates remain source records only"
    - "Cross-process complete-run exclusion proven across batch commits via pg_try_advisory_lock while independent sources remain processable; injected batch failure rolls back rows/counts/checkpoint atomically, retains reconciled partial counts with a redacted error category, and resume converges without duplicates"
    - "Contact leakage scans prove phone/handle values absent from extraction_json, excerpts, masked text, and error summaries; Polish/Cyrillic/supplementary/combining fixtures prove persisted half-open offsets reproduce Python str slicing of the exact preserved flattened text"
    - "No availability boolean, ContactPoint, geocoder, media copy, public API change, or destructive cleanup introduced; OpenAPI contract unchanged"
    - "Local CI parity: ruff, strict mypy, import-linter 11 contracts kept, architecture probe, pip-audit, 207 tests at 94.79% coverage against pinned PostGIS"
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# E3-T2: Implement idempotent persistence and reprocessing

> Promoted after owner-approved spike revision 3. Status remains `draft` until implementation-plan revision 3 is owner-approved and remaining gates are satisfied. No code may start from this file yet.

## Outcome

Persist source messages, checksum revisions, canonical offers, contact-free field provenance, ingest runs, and resumable checkpoints so unchanged or changed replay converges without acknowledging uncommitted work.

## Original roadmap definition

- Priority/size: P0 / L
- Dependencies: E2-T2, E3-T1
- Work:
  - Upsert source messages/revisions.
  - Persist provenance, canonical offers, relationships, checkpoints, and ingest runs.
  - Add advisory locking and bounded transactions.
- Acceptance:
  - Replaying a fixture converges without duplicate source records/offers/media links.
  - Changed source payload creates a revision.
  - Cancellation/failure leaves a resumable checkpoint and report.

## Scope

- Add forward Alembic migrations and SQLAlchemy mappings for source channels/messages/revisions, developments, offer-source relationships, and ingest runs while keeping the current M1 catalog compatible.
- Add framework-independent run/checkpoint/persistence values and narrow application-owned unit-of-work/repository ports.
- Upsert exact source identity by platform/channel/message ID. Snapshot every source version: initial ingestion creates immutable revision 1, each changed checksum appends the complete new representation, and the current message points to its matching immutable revision. Use exact source relationships rather than a fuzzy fingerprint as the replay key.
- Hold one session-level PostgreSQL advisory lock for the complete source/channel run, including across bounded batch commits. An alternative durable lease must have renewable expiry, owner identity, fencing/takeover semantics, and equivalent cross-process exclusion.
- Keep row work, counts, and the checkpoint they acknowledge in the same bounded transaction; never hold a row transaction over source iteration, provider calls, media I/O, or report rendering.
- Raw payload/source text remains restricted lineage. Persisted `extraction_json`, `source_text_excerpt`, public projections, routine logs/reports, indexes, diagnostics, and errors must omit plaintext `ContactSpan` values and any contact-bearing span text.
- Preserve the exact flattened E2 `RawMessage.text` string in every source revision without Unicode normalization or other mutation. Persist every provenance span as zero-based half-open Python `str` offsets (`preserved_text[start:end]` using Unicode code-point indexing), never UTF-8 byte or UTF-16 code-unit offsets.
- Do not create `ContactPoint` rows. E6-T5 owns encrypted/HMAC contact persistence and reveal.

## Acceptance criteria

- [ ] Empty and previous-head PostGIS databases upgrade to the new head; repeated upgrade is a no-op and current seed/public reads remain compatible.
- [ ] Initial ingestion creates exactly revision 1 and a valid current-revision reference; unchanged replay creates no revision; a changed payload creates exactly one ordered complete snapshot and atomically advances the current reference.
- [ ] Every current and historical source version is resolvable through `SourceMessageRevision`, and current checksum/text/payload equals the referenced snapshot.
- [ ] Every accepted candidate has an exact source relationship and deterministic contact-free field provenance bound to the immutable source revision whose preserved text was parsed; non-candidates remain source records.
- [ ] Polish/Cyrillic, supplementary-character, and combining-mark fixtures prove persisted half-open offsets reproduce slicing of the exact preserved flattened E2 string, with no normalization/mutation and no copied span text.
- [ ] A failed bounded transaction rolls back its rows/counts/checkpoint; resume starts after the last committed checkpoint and converges while the same run-level lock/lease remains owned.
- [ ] Cross-process attempts for one source are rejected for the complete run, including between batch commits, while independent sources remain processable.
- [ ] Failed/cancelled runs retain reconciled partial counts and a redacted error category without contacts, payload, internal paths, or credentials.
- [ ] Tests inject phone/handle/email-like `ContactSpan` values and prove none appear in `extraction_json`, excerpts, public/operational DTOs, logs, reports, indexes, or errors.
- [ ] No availability boolean, `ContactPoint`, geocoder, media copy, public API, production activation, or destructive cleanup behavior is introduced.

## Test plan

- Unit: initial/current revision decisions, money/range conversion, contact-free provenance serialization, exact flattened multilingual Python-string offset slicing, checkpoint/count invariants, lease/lock ownership, cancellation/error redaction, and port fakes.
- Integration: clean/prior migration, revision-1/current-pointer constraints, unchanged/changed replay, current-snapshot equality, two-process run contention across multiple commits, owner failure/lease takeover where applicable, injected batch failure, resume, and seed/public-read compatibility.
- Contract/security: SQLAlchemy metadata/head readiness, import-linter framework independence, forbidden availability/contact columns, and payload/contact canary leakage scans.
- End-to-end: sanitized E2 fixture through the persistence boundary twice against disposable PostGIS.

## Dependencies and traceability

- Task dependencies: [E2-T2](../../E2-historical-export-parser-audit/tasks/E2-T2-implement-candidate-detection-and-typed-extractors.md), [E3-T1](E3-T1-create-schema-and-migrations.md)
- Milestone: [M1](../../../milestones/M1-vertical-proof.md).
- Traceability: [Product requirements](../../../product/EXPERIENCE.md), [Decision registry](../../../decisions/README.md), [Data model](../../../contracts/DATA_MODEL.md), [Ingestion](../../../ingestion/README.md), [Security](../../../security/README.md).

## Approval and start boundary

- Spike gate is satisfied for revision 3. Implementation remains blocked until owner approval of implementation-plan revision 3 and remaining dependency/deferred gates required by the workflow.
- After authorization and completed dependencies, this task starts from then-current `main` on a dedicated E3-T2 branch and opens a PR targeting `main`.
- Production code, migrations, scaffolds, infrastructure changes, and disposable proof code remain out of scope while status is `draft` and the implementation gate is blocked.

## Affected modules and contracts

- See the approved/awaiting [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) revision 3 sequence entry for this task and [DATA_MODEL.md](../../../contracts/DATA_MODEL.md).

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
- [x] The branch and pull request contain this task only.
- [x] `branch.name` and `branch.created_at` are recorded before setting `in_progress`.

## Done checklist

- [x] Acceptance criteria pass.
- [x] The global [definition of done](../../../workflow/DEFINITION_OF_DONE.md) passes.
- [x] Completion actor, time, pull request, and evidence are recorded.
