---
schema: ai-workflow/task@1
id: E17-T2
epic: E17
title: "Parser replay re-import"
status: ready
revision: 1
priority: P1
size: M
milestone: M5
dependencies: [- E17-T1]
requirement_ids: []
decision_ids: []
deferred_decision_ids: []
promotion:
  source: ../proposed-tasks/E17-T2-parser-replay-reimport.md
  promoted_by: "ZCode agent under owner instruction"
  promoted_at: "2026-08-29T17:10:10Z"
spike_gate:
  status: satisfied
  file: ../SPIKE.md
  approved_revision: 1
  verified_by: "ZCode agent under owner instruction"
  verified_at: "2026-08-29T17:10:10Z"
implementation_gate:
  status: satisfied
  file: ../IMPLEMENTATION_PLAN.md
  approved_revision: 1
  verified_by: "ZCode agent under owner instruction"
  verified_at: "2026-08-29T17:10:10Z"
dependency_gate:
  status: satisfied
  verified_by: "ZCode agent under owner instruction"
  verified_at: "2026-08-29T17:10:10Z"
  evidence: []
branch:
  required: true
  name: feat/E17-T2-parser-replay-reimport
  task_id: E17-T2
  one_task_only: true
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---


# E17-T2: Parser replay re-import

## Outcome

An operator command re-derives canonical offers and locations from the retained raw
archive for a target parser version, making "update the parser, then re-import" a
first-class, replay-safe operation that needs no Telegram traffic and no
operator-staged export.

## Scope

- `wef-import`-family command (explicit importer operation per deployment governance,
  never a hidden Alembic data migration) that selects raw-derived canonical rows whose
  stored `parser_version` is older than the target and re-runs extraction from the
  retained raw event payloads.
- Replayed messages reuse the existing offer upsert path with edit-equivalent
  semantics (same revision anchoring, visibility, and dedup fingerprint rules as a
  revised message) so replay cannot diverge from organic edits.
- Checkpointed, resumable, idempotent: a completed replay is a no-op on re-run.
- Integrates with the geocode stage under ADR-021/D-002 budgets and keeps the
  "Unknown location" sentinel exclusion from PR #197.
- Scope selectors: by parser-version threshold, and optionally restricted to rows tied
  to the unknown-location sentinel for minimal blast radius.

## Out of scope

- Reprocessing media binaries (media metadata replay only), and any frontend change.

## Work

- Selection and replay must be deterministic and ordered by source identity; progress
  surfaces reuse the existing run/checkpoint reporting.
- The command records an ingest run in `reprocess` mode, activating the previously
  unused `RunMode.REPROCESS` value with real semantics.

## Acceptance criteria

- [ ] Replaying a fixture corpus twice produces identical canonical state (offers,
      locations, extraction JSON) with zero provider calls on the second run.
- [ ] A stale-parser offer with no location gains its pin-line location after replay
      with the `e2-v4`+ parser, while checksum-untouched raw history remains intact.
- [ ] Replay is bounded by the existing durable budget/pause controls and never
      fans out geocode providers beyond policy.
- [ ] Operator evidence is redacted: no source text or secrets in run summaries.

## Dependencies and gates

- E17-T1 (raw archive is the replay source).
- ADR-021 geocode budget machinery; E15 checkpoint/liveness conventions.

## Risks and notes

- Blast radius on offer visibility and dedup fingerprints — mitigated by reusing the
  revised-offer path unchanged; needs an explicit regression test.
- Replay volume vs Geoapify daily quota — cached queries are free; budget pauses
  rather than overruns.

## Promotion checklist

- [ ] The epic spike is explicitly owner-approved for its current revision.
- [ ] Scope, acceptance, dependencies, priority, size, and traceability match the
      approved spike.
- [ ] Required deferred decisions are resolved.
- [ ] The file will be moved—not copied—to the epic's `tasks/`.
- [ ] Promotion metadata will identify the target, promoter, and timestamp.
