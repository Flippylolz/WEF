---
schema: ai-workflow/spike@1
epic: E2
title: "Historical export parser and audit research"
status: draft
revision: 1
owner: owner
research_only: true
code_allowed: false
decision_ids: [ADR-003, ADR-006, ADR-007, ADR-012]
domain_docs: [data, ingestion, contracts, security]
proposed_task_ids: [E2-T1, E2-T2, E2-T3, E2-T4, E2-T5]
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

# Spike: Historical export parser and audit

> This is a draft research scope. It authorizes documentation/research only: no production code, scaffold, migration, infrastructure/configuration change, generated executable artifact, prototype, proof branch, or disposable proof code.

## Question

How should the historical Telegram export be streamed, classified, parsed, grouped, and audited so every input record reconciles while uncertain values and sensitive source material remain explicit?

## Context and constraints

- The 21 MB JSON must be processed without whole-file loading.
- Historical and future Telegram inputs share a canonical RawMessage boundary under ADR-006.
- Unknown, conflicting, malformed, or unassociated data remains null/reviewable/reportable and is never invented.
- Dry runs may persist isolated ingest-run metadata/report artifacts only; they do not write source, offer, location, geocode, or media state.

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

Review the source baseline, ingestion rules, data model, known Telegram Desktop JSON shapes, redaction requirements, and reconciliation counters. Define fixture/golden-test questions without inspecting or copying private payload into planning files.

Research outputs must remain non-executable Markdown. Any data inspection must preserve source privacy and may not copy real source payload, contacts, credentials, sessions, or media into this artifact.

## Current evidence baseline

- The roadmap names string/mixed text, service, photo, video, reply, malformed, grouped-ID, and historical time-burst cases.
- DATA requires stable reason codes, redacted representative samples, source checksums, parser versions, and stage-count reconciliation.
- Product requirements prohibit invented availability and require confidence/provenance for shown fields.

These are planning facts and constraints, not evidence that implementation or acceptance checks have run.

## Options to evaluate

- Use a streaming historical adapter plus versioned typed extractors and explicit media-association rules.
- Load the full export into memory, which is unnecessary and weakens bounded processing.
- Use a permissive best-effort parser without reconciliation, which would hide omissions and overconfident extraction.

## Draft recommendation

Define one streaming adapter, a synthetic/redacted fixture corpus, versioned candidate/extractor rules, confidence-bearing media associations, and deterministic dry-run/audit reports before any full import.

This recommendation remains draft and may change after bounded research. It is not approved and does not authorize any proposed task.

## Proposed task boundaries

- [E2-T1: Implement source adapter and fixture corpus](proposed-tasks/E2-T1-implement-source-adapter-and-fixture-corpus.md) — candidate boundary for spike refinement.
- [E2-T2: Implement candidate detection and typed extractors](proposed-tasks/E2-T2-implement-candidate-detection-and-typed-extractors.md) — candidate boundary for spike refinement.
- [E2-T3: Implement media grouping](proposed-tasks/E2-T3-implement-media-grouping.md) — candidate boundary for spike refinement.
- [E2-T4: Implement dry-run reports](proposed-tasks/E2-T4-implement-dry-run-reports.md) — candidate boundary for spike refinement.
- [E2-T5: Audit the complete export](proposed-tasks/E2-T5-audit-the-complete-export.md) — candidate boundary for spike refinement.

No candidate above may appear in an executable implementation-plan sequence while it remains under `proposed-tasks/`.

## Risks and open questions

- Template drift can create false positives or silently skip records.
- Time-burst grouping can merge adjacent galleries without explicit boundaries.
- Reports or fixtures can leak phone numbers, mentions, or payload text if redaction is not designed first.
- Confirm task-level traceability, cross-epic dependencies, test evidence, rollout, and rollback during spike refinement.
- Resolve every named deferred-decision gate before promoting affected work.

## Invalidation triggers

- A change to this epic's outcome, accepted architecture/dependency direction, public or persisted contracts, security model, ingestion semantics, or deployment topology.
- A new external dependency or service that changes data handling, operations, licensing, secrets, or replacement paths.
- Evidence that a listed task boundary cannot remain independently reviewable or that a roadmap dependency is incomplete.

## Exit checklist

- [ ] The bounded question is answered with evidence and uncertainty distinguished.
- [ ] Governing domain documents and decisions are reviewed and linked.
- [ ] Options, recommendation, risks, and open questions are complete.
- [ ] Proposed task scope, acceptance, dependencies, priority/size, and traceability are refined.
- [ ] No production or disposable proof code was created.
- [ ] `revision` represents the material content being submitted.
- [ ] Status is changed to `awaiting_approval` while approval remains `pending`.

## Owner decision

The owner records the decision only in the YAML `approval` object. Approval of the current spike revision would permit task refinement/promotion and implementation planning only; it would not permit code.
