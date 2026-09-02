---
schema: ai-workflow/implementation-plan@1
epic: E23
title: "Location display name normalization delivery"
status: approved
revision: 1
owner: owner
spike_revision: 1
task_sequence:
  - id: E23-T1
    revision: 1
  - id: E23-T2
    revision: 1
approval:
  required_role: owner
  status: approved
  decided_by: "Flippylolz"
  decided_at: "2026-09-02T20:32:00Z"
  approved_revision: 1
  evidence: "Owner message in Cursor: 'continue' after E23 implementation plan draft review."
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# Implementation Plan: Location display name normalization delivery

## Approved spike baseline

[Spike revision 1](SPIKE.md) is owner-approved. Binding decisions:

- Polish-forward Option 2 template mapping and decoration stripping.
- Verified locations are exempt from bulk rename.
- Near-suburb locations stay visible; badge/filter work is deferred.

## Scope and outcome

Deliver canonical location display-name normalization for new locations, then an
idempotent operator backfill for existing non-verified rows, without changing
`normalized_address_hash`, geocoding, or E18 verified names.

Exclusions: transliteration of Latin street tokens; dual-language aliases;
near-suburb badge/filter; generic admin bulk edit forms.

## Ordered task sequence

### 1. E23-T1 — Add canonical location display-name normalization

- Task: [E23-T1 revision 1](tasks/E23-T1-display-name-normalization.md).
- Dependency: completed E17-T2.
- Independent result: new locations get Polish-forward names; existing hashes stay
  write-once.
- Modules: ingestion location naming / `_resolve_location` path, fixtures/tests,
  data-model/ingestion docs as needed.
- Verification: measured Cyrillic/fragment fixtures; hash stability; write-once
  behavior for existing rows.
- Rollout: deploy with new naming only (additive behavior for new rows).
- Rollback: prior application image; already-written new names remain unless a
  later backfill revises non-verified rows.

### 2. E23-T2 — Backfill non-verified location display names

- Task: [E23-T2 revision 1](tasks/E23-T2-display-name-backfill.md).
- Dependency: E23-T1.
- Independent result: operators can dry-run/apply renames safely.
- Modules: operator CLI, reporting, OPERATOR_COMMANDS runbook.
- Verification: dry-run counts, verified skip, hash guard, idempotent apply.
- Rollout: dry-run → review → `--apply` → idempotency re-run.
- Rollback: application rollback stops further renames; restoring prior names
  requires an explicit recovery procedure (no automatic undo).

## Cross-task architecture

- Display-name rules live in the ingestion/catalog naming path owned by the
  backend. The frontend continues to render stored `display_name` /
  `display_address` projections only.
- Identity remains `normalized_address_hash`. Normalization must never feed the
  hash input.
- E23-T2 reuses retained raw evidence and the E23-T1 pure naming function; it does
  not invent a second template language.

## Data and migrations

- No identity-column migration is required for the naming rules themselves.
- Backfill updates display fields only for non-verified locations.
- Preserve write-once semantics for ordinary ingestion after a location exists.

## Security and privacy

- No new public PII fields. Reports are aggregate/redacted.
- No external provider calls.

## Test and verification strategy

- Unit fixtures for Cyrillic templates, decoration, and fragment lines.
- Integration: create-new vs existing-hash write-once; backfill skip verified.
- Operational: production dry-run/apply checklist in operator docs.

## Operations, rollout, and rollback

1. Merge/deploy E23-T1.
2. Merge/deploy E23-T2 CLI.
3. Dry-run on production, review counts, apply, confirm idempotency.
4. Manually curate residual fragment-only names in E18 when needed.

## Risks and mitigations

- **Hash drift:** isolate naming from hash inputs; assert equality in tests/backfill.
- **Over-normalization:** keep Latin street tokens; narrow label maps only.
- **Verified overwrite:** hard skip verified review status.

## Invalidation triggers

Return to the spike if template language policy, verified exemption, or identity
rules change. Return to this plan for sequence/module/test/rollout changes.

## Approval checklist

- [x] Referenced spike revision is owner-approved and current.
- [x] Sequence entries are promoted tasks with acceptance criteria.
- [x] Dependencies are acyclic and enforceable.
- [x] Modules, tests, rollout, and rollback are explicit.
- [x] Owner approves this plan revision before implementation code starts.

## Owner decision

Flippylolz approved plan revision 1 on 2026-09-02 via Cursor message `continue`.
