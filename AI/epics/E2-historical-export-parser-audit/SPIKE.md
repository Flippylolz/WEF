---
schema: ai-workflow/spike@1
epic: E2
title: "Historical export parser and audit research"
status: approved
revision: 3
owner: owner
research_only: true
code_allowed: false
decision_ids: [ADR-003, ADR-006, ADR-007, ADR-012]
domain_docs: [data, ingestion, contracts, security]
proposed_task_ids: [E2-T1, E2-T2, E2-T3, E2-T4, E2-T5]
approval:
  required_role: owner
  status: approved
  decided_by: Flippylolz
  decided_at: "2026-08-13T18:58:46Z"
  approved_revision: 3
  evidence: "Owner explicitly directed implementation of the complete E2 epic and approved the attached Complete E2 Historical Parser Epic scope"
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# Spike: Historical export parser and audit

> Revision 3 is approved research. It authorizes promotion and planning for E2-T2 through E2-T5, including the additive source-neutral media-group boundary; code remains governed by the separately approved implementation plan.

## Question

How should the historical Telegram export be streamed, classified, parsed, grouped, and audited so every input record reconciles while uncertain values and sensitive source material remain explicit?

## Context and constraints

- The 21,634,277-byte JSON must be processed without whole-file loading.
- Historical and future Telegram inputs share a canonical RawMessage boundary under ADR-006.
- Unknown, conflicting, malformed, or unassociated data remains null/reviewable/reportable and is never invented.
- Dry runs may persist isolated ingest-run metadata/report artifacts only; they do not write source, offer, location, geocode, or media state.
- The current M1 map seed remains synthetic; E2-T1 establishes the source boundary and safe real-shape corpus without changing database, API, or browser data.

Governing domains:

- [Data](../../data/README.md)
- [Ingestion](../../ingestion/README.md)
- [Contracts](../../contracts/README.md)
- [Security](../../security/README.md)

Governing decisions and deferred gates:

- [ADR-003](../../decisions/adr/ADR-003-do-not-infer-current-availability.md)
- [ADR-006](../../decisions/adr/ADR-006-shared-ingestion-core.md)
- [ADR-007](../../decisions/adr/ADR-007-mounted-media-storage-interface.md)
- [ADR-012](../../decisions/adr/ADR-012-backend-centric-modular-monolith.md)

## Research method

Review the source baseline, ingestion rules, data model, Telegram Desktop JSON shapes, redaction requirements, reconciliation counters, and current `ijson` streaming behavior. Inspect only aggregate/non-sensitive properties of the ignored local export; do not copy source payload into planning files.

Research outputs must remain non-executable Markdown. Any data inspection must preserve source privacy and may not copy real source payload, contacts, credentials, sessions, or media into this artifact.

## Evidence

The ignored `est-test/result.json` was inspected read-only on 2026-08-13. No payload text, contact, or media was emitted or copied:

- File size: 21,634,277 bytes.
- SHA-256: `d349e27003058f470fa53e5cd9004fe6759e8db466bc690f132398e038816249`.
- Top-level shape: `id`, `messages`, `name`, and `type`; channel type is `public_channel`.
- Date range: 2024-07-11 through 2026-08-12.
- Record reconciliation: 27,082 total = 27,075 message + 7 service records.
- Text representation: 23,834 string values and 3,248 mixed arrays; mixed arrays contain strings plus typed `{type,text}` spans and one observed link span with `href`.
- Media/relationship shape: 26,991 photo records, 78 file/video records, 11 replies, and 23,821 empty string captions. Media and reply counts are orthogonal to the primary record classification.
- Contact-like risk: aggregate scans found 3,235 records matching a broad phone-like pattern and 2,323 matching a Telegram-mention pattern. These are risk indicators, not audited contact counts, and prohibit committing a random source slice.

- The roadmap names string/mixed text, service, photo, video, reply, malformed, grouped-ID, and historical time-burst cases.
- DATA requires stable reason codes, redacted representative samples, source checksums, parser versions, and stage-count reconciliation.
- Product requirements prohibit invented availability and require confidence/provenance for shown fields.
- Current iJSON documentation confirms that `ijson.items(binary_file, "messages.item")` iterates objects with constant memory and raises typed `IncompleteJSONError`/`JSONError` failures for truncated or invalid documents.

These facts answer the spike question but are not implementation or acceptance-test evidence.

## Options evaluated

1. Use a streaming historical adapter plus versioned typed extractors and explicit media-association rules. This satisfies the bounded-memory, shared-core, and audit requirements.
2. Load the full export into memory. Rejected: unnecessary, harder to bound, and inconsistent with the ingestion contract.
3. Use a permissive best-effort parser without reconciliation. Rejected: it can silently omit records and overstate extraction certainty.

## Approved recommendation

Implement one historical adapter in the backend ingestion feature:

- Preflight top-level/channel metadata with bounded reads, then stream `messages.item` from a binary file through `ijson`. The export may be read in multiple bounded passes; no pass may materialize the message array or full document.
- Calculate the exact export SHA-256 over source bytes and a deterministic per-record SHA-256 over canonical UTF-8 JSON (`sort_keys`, compact separators, Unicode preserved).
- Convert Unix timestamp fields to timezone-aware UTC; preserve original date strings in the raw payload and never infer local timezone from them.
- Stop source-specific behavior at a framework-independent `RawMessage` contract containing platform/channel identity, external/reply IDs, published/edited timestamps, message type, exact flattened text, original text/entities, media descriptors, raw payload, and checksum.
- Preserve mixed text order exactly by concatenating string segments and each typed segment's `text`; retain the original mixed representation and entity objects for later extractors.
- Emit one result for every `messages` array item. Exactly one primary classification (`service`, `photo`, `video`, `text`, `empty`, `unhandled`, or `malformed`) participates in reconciliation; mixed-text and reply are orthogonal counters.
- Represent structurally malformed records as typed rejected results with stable reason codes, source index, and payload checksum. Invalid/truncated top-level JSON or channel mismatch fails the source scan before canonical writes and reports only redacted metadata/counts.
- Preserve unknown fields in the internal raw payload. E2-T1 does not detect candidates, group media, persist source/canonical rows, produce the final dry-run report, or replace the synthetic M1 map seed.
- Add an optional source-neutral media-group ID to `RawMessage` in E2-T3 so historical and future live adapters can expose explicit grouping without downstream Telegram-specific payload access.
- Preserve complete source values in `RawMessage` and future internal persistence. Sanitization applies to committed fixtures; masking/redaction applies to routine logs, report samples, and public presentation rather than destructively altering internal source evidence.

## Safe fixture corpus

Commit a small reviewed corpus derived from observed historical shapes, not a random export slice:

- Rebase channel/message/reply IDs and dates; replace channel display identity.
- Remove phone numbers, Telegram handles, agent names, and other contact/source identity.
- Replace source media names/paths and omit all media bytes.
- Generalize identifying addresses and numeric business values while retaining only the Unicode, whitespace, mixed-text/entity, and descriptor structure needed by the adapter test.
- Include string text, mixed text/entity/link, service, photo, video/thumbnail, reply, and empty-caption source-derived cases.
- Add explicitly synthetic structurally malformed and truncated-document cases.
- Store golden `RawMessage`, classification, checksum, and count expectations for the sanitized bytes.
- Add a fixture-safety test that rejects contact-like patterns, real channel identity, absolute/traversal paths, and unreviewed binary/media files.

The corpus bridges real export shapes into deterministic CI while the immutable export, media, and any source-derived sensitive report remain ignored and outside Git, CI artifacts, logs, and images.

## Proposed task boundaries

- [E2-T1: Implement source adapter and fixture corpus](tasks/E2-T1-implement-source-adapter-and-fixture-corpus.md) — completed source boundary.
- [E2-T2: Implement candidate detection and typed extractors](tasks/E2-T2-implement-candidate-detection-and-typed-extractors.md) — approved for promotion and implementation planning.
- [E2-T3: Implement media grouping](tasks/E2-T3-implement-media-grouping.md) — approved for promotion and implementation planning after E2-T2.
- [E2-T4: Implement dry-run reports](tasks/E2-T4-implement-dry-run-reports.md) — approved for promotion and implementation planning after E2-T2/E2-T3.
- [E2-T5: Audit the complete export](tasks/E2-T5-audit-the-complete-export.md) — approved for promotion and implementation planning after E2-T4.

Implementation-plan revision 3 may sequence E2-T2 through E2-T5. Each task remains independently gated and uses one dedicated branch and pull request.

## Risks and open questions

- A source export with a changed top-level/channel shape must fail closed with a redacted typed error.
- Template drift can create false positives or silently skip records in later candidate/extractor work.
- Time-burst grouping can merge adjacent galleries without explicit boundaries.
- Reports or fixtures can leak phone numbers, mentions, or payload text if redaction is not designed first.
- iJSON returns decoded object values rather than original per-record byte spans, so per-record checksums must use the approved canonical JSON form while the export checksum remains byte-exact.
- A consumer that stops iteration early cannot claim a complete checksum/reconciliation result; the adapter result must distinguish incomplete from complete scans.
- E2-T2 through E2-T5 have no unresolved deferred decision; their ordered task and dependency gates remain mandatory.

## Invalidation triggers

- A change to this epic's outcome, accepted architecture/dependency direction, public or persisted contracts, security model, ingestion semantics, or deployment topology.
- A new external dependency or service that changes data handling, operations, licensing, secrets, or replacement paths.
- Evidence that a listed task boundary cannot remain independently reviewable or that a roadmap dependency is incomplete.

## Exit checklist

- [x] The bounded question is answered with evidence and uncertainty distinguished.
- [x] Governing domain documents and decisions are reviewed and linked.
- [x] Options, recommendation, risks, and open questions are complete.
- [x] E2-T1 through E2-T5 scope, acceptance, dependencies, priority/size, and traceability are refined.
- [x] No production or disposable proof code was created.
- [x] Revision 3 represents the approved complete-epic material content.
- [x] Status and approval metadata record the owner's spike-only decision.

## Owner decision

Flippylolz approved revision 3 by explicitly directing implementation of the complete E2 epic against the attached Complete E2 Historical Parser Epic plan. This permits promotion and implementation planning for E2-T2 through E2-T5. The separately recorded implementation-plan approval governs code authorization.
