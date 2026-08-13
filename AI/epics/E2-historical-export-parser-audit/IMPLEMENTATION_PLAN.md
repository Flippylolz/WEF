---
schema: ai-workflow/implementation-plan@1
epic: E2
title: "Historical export parser and audit implementation plan"
status: approved
revision: 3
owner: owner
spike_revision: 3
task_sequence:
  - id: E2-T2
    revision: 2
  - id: E2-T3
    revision: 2
  - id: E2-T4
    revision: 2
  - id: E2-T5
    revision: 2
approval:
  required_role: owner
  status: approved
  decided_by: Flippylolz
  decided_at: "2026-08-13T18:58:46Z"
  approved_revision: 3
  evidence: "Owner accepted the attached Complete E2 Historical Parser Epic execution plan and explicitly directed implementation of the whole epic as four task PRs"
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# Implementation Plan: Historical export parser and audit

## Approved spike baseline

[E2 spike revision 3](SPIKE.md) retains the completed constant-memory source adapter and approves the remaining parser, media grouping, dry-run reporting, and complete-export audit boundaries. It also approves an optional source-neutral media-group ID and distinguishes complete internal source evidence from sanitized fixtures and redacted logs/report samples/public presentation.

## Scope and outcome

Deliver [E2-T2](tasks/E2-T2-implement-candidate-detection-and-typed-extractors.md), [E2-T3](tasks/E2-T3-implement-media-grouping.md), [E2-T4](tasks/E2-T4-implement-dry-run-reports.md), and [E2-T5](tasks/E2-T5-audit-the-complete-export.md) as four sequential task PRs.

The result is a deterministic, versioned listing parser with explicit provenance/confidence, bounded media association, reconciled machine/human dry-run reports, and a reproducible audit of all 27,082 source records. E2 does not persist canonical data, geocode, copy media, alter public APIs, or replace the synthetic map seed.

## Ordered task sequence

### 1. E2-T2 — Candidate detection and typed extractors

- Depends on completed [E2-T1](tasks/E2-T1-implement-source-adapter-and-fixture-corpus.md) through merged [PR #33](https://github.com/Flippylolz/WEF/pull/33).
- Add immutable candidate, score/reason, source-span, confidence, warning, typed-range, link/contact-span, and extraction-bundle contracts.
- Implement deterministic `e2-v1` development/unit candidate rules and extractors for market/content type, location/district, development name, apartment/parking/storage values, included flags, area, rooms, floor, delivery, links, and contact spans.
- Preserve source text/payload unchanged; unknown/conflicting values remain null/reviewable and availability is never inferred.
- Verify sanitized multilingual/range/negative goldens, synthetic runtime contact cases, exact provenance, deterministic versions, architecture, coverage, and repository CI.

### 2. E2-T3 — Deterministic media grouping

- Depends on E2-T1 and completed E2-T2 because historical grouping consumes the versioned candidate result.
- Add the optional source-neutral media-group ID to `RawMessage` and adapter conversion.
- Emit ordered associations with rule/confidence using same-message, explicit group, reply, and 120-second historical time-burst evidence.
- Preserve source ownership and reconcile associated plus unassociated media without file access.
- Verify service/reply/gap boundaries and two nearby listing galleries that must remain separate.

### 3. E2-T4 — Dry-run reports and operator wiring

- Depends on completed E2-T2 and E2-T3.
- Stream source, detection, extraction, and grouping through one application orchestrator.
- Write atomic JSON and Markdown reports containing source/parser identity, date range, reconciled stage/reason/media buckets, timings, and terminal state.
- Exclude or mask contacts, raw payload samples, internal paths, and source text in routine logs/report samples while retaining complete in-memory source evidence.
- Extend bounded operator wiring without source/canonical/geocode/media writes or media copies.

### 4. E2-T5 — Complete export audit

- Depends on completed E2-T4.
- Run the pipeline read-only over the ignored export after verifying the approved byte size and SHA-256.
- Reconcile all 27,082 records, review candidate/rule/template/media gaps, explain differences from exploratory counters, and add only sanitized fixtures plus versioned rule fixes.
- Commit a non-sensitive `AUDIT.md` with parser/source identity, aggregate counts, uncertainty, reviewed gap categories, and reproducibility evidence.

## Architecture and dependency direction

- Domain owns immutable source, candidate, extraction, association, and report values. Application owns deterministic rules, grouping, orchestration, reconciliation, and ports. Infrastructure remains limited to iJSON source conversion and atomic report output.
- Reuse canonical catalog `ContentType`/`MarketType` rather than duplicate product semantics. Catalog and interfaces never import ingestion infrastructure.
- Domain/application remain independent of iJSON, FastAPI, Pydantic, SQLAlchemy, settings, and report filesystem concerns; `.importlinter` and negative probes enforce the boundary.
- No new parser framework is required. Python standard-library regex/decimal/URL behavior remains deterministic and locale-independent.
- The pipeline streams records and retains only one record, active group state, counters, bounded samples, and a minimal message-ID index; no stage materializes the source document or all raw messages.
- Parser/rule changes use explicit versions. T5 may change `e2-v1` behavior only with a version bump, golden updates, full reconciliation, and documented audit evidence.

## Contracts, persistence, and compatibility

- No migration, SQLAlchemy model, database transaction, public HTTP/OpenAPI/frontend change, geocoding request, or media copy.
- `RawMessage` and future internal persistence retain complete source identity/text/entities/payload/contact evidence. Only committed fixtures and routine logs/report samples/public presentation are sanitized or masked.
- E2-T4 writes only configured ignored report artifacts; it does not persist `SourceMessage`, `Offer`, `Location`, `ContactPoint`, `GeocodeResult`, `MediaAsset`, or canonical `IngestRun` rows.
- Reports use a stable schema/version and never claim completion from a partial or failed scan.
- E3-T2/E3-T5 later own database schema/persistence and production promotion of the audited data.

## Test and verification strategy

- Unit/golden tests cover candidate reasons/thresholds, typed values/ranges, exact spans, confidence/warnings, null/conflict behavior, parser versions, media rules/boundaries, report reconciliation/redaction, and atomic output.
- Negative cases include non-listing token overlap, missing/ambiguous values, unknown/non-PLN currency, conflicting high-confidence values, close galleries, unsafe partial summaries, cancellation, and I/O failures.
- Contact-shaped values appear only in synthetic runtime tests; committed source-derived fixtures remain sanitized and pass identity/contact/path/binary scans.
- T2-T4 acceptance uses deterministic CI fixtures. T5 additionally runs the ignored export locally and emits only approved aggregate/redacted evidence.
- Every PR runs frozen install, Ruff, strict mypy, import-linter/negative proof, branch-coverage pytest, dependency audit, OpenAPI/frontend drift checks, production builds, repository safety, and required GitHub CI.

## Rollout and rollback

The remaining E2 work is inert parser/report library and operator code with no canonical persistence or production activation. Roll back any task by reverting its squash commit; no data restoration, schema downgrade, media cleanup, or deployment ordering is required.

Deliver in strict order: E2-T2, E2-T3, E2-T4, E2-T5. Each starts from the latest `main` after its predecessor is merged, uses one dedicated branch/PR, records completion evidence after an initial green run, reruns CI after that evidence commit, and squash-merges only when all required jobs are successful.

## Risks and mitigations

- **False-positive/overconfident extraction:** weighted versioned reasons, negative fixtures, exact provenance, warnings, null/review outcomes, and no availability inference.
- **Range/currency corruption:** Decimal/integer typed ranges, no midpoint, no inferred zeros, and no default PLN for unknown currency.
- **Gallery false merge:** explicit evidence priority, stop boundaries, rule/confidence, and close-consecutive-listing goldens.
- **Report/privacy leak:** complete data remains internal; bounded redacted samples, no payload/path/contact logs, atomic ignored outputs, and safety scans.
- **Unreconciled audit:** exact source checksum/parser version, stage invariants, deterministic report hash, reason buckets, and repeated T5 audit after each rule change.
- **Scope creep into E3:** import-linter and task acceptance prohibit database, geocoding, media storage/copy, and public API behavior.

## Invalidation triggers

Return to the spike for any further material `RawMessage` identity/checksum/timestamp/grouping change, destructive raw-data redaction, new parser/service architecture, database/public contract, geocoding/media operation, or changed epic outcome. Return to this plan for material task dependency, rule/report schema, confidence/reconciliation, fixture, CLI, test, rollout, or rollback changes.

## Approval checklist

- [x] E2 spike revision 3 has explicit owner approval and remains current.
- [x] E2-T2 through E2-T5 revision 2 are promoted with complete acceptance criteria and traceability.
- [x] The T1 → T2 → T3 → T4 → T5 sequence is complete, acyclic, and enforceable.
- [x] Modules, contracts, data handling, tests, reports, risks, rollout, and rollback are explicit.
- [x] No task has an unresolved deferred decision or migration.
- [x] No remaining E2 implementation code was written before revision 3 approval.
- [x] Revision 3 and its separate owner approval are recorded.

## Owner decision

Flippylolz separately approved implementation-plan revision 3 by accepting the attached Complete E2 Historical Parser Epic plan and directing implementation as four task PRs. This authorizes only E2-T2 through E2-T5 under the sequence, boundaries, tests, and merge gates above.
