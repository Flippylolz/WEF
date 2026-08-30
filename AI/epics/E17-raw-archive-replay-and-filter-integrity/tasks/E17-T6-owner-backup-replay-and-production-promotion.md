---
schema: ai-workflow/task@1
id: E17-T6
epic: E17
title: "Owner backup replay and production promotion"
status: done
revision: 1
priority: P1
size: L
milestone: M5
dependencies: [E17-T1, E17-T2, E17-T3, E17-T4, E17-T5]
requirement_ids: []
decision_ids: []
deferred_decision_ids: []
promotion:
  source: ../proposed-tasks/E17-T6-owner-backup-replay-and-production-promotion.md
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
note: "Owner-gated: epic completion waits on the owner-supplied backup replay and production promotion (see epic README)."
branch:
  required: true
  name: doc/E17-T6-owner-backup-replay-and-production-promotion
  task_id: E17-T6
  one_task_only: true
completion:
  completed_by: "ZCode agent under owner instruction"
  completed_at: "2026-08-30T08:30:00Z"
  pull_request: "https://github.com/Flippylolz/WEF/pull/211"
  evidence:
    - "Owner supplied the fresh backup est-test/data-30-09-2026/result.json: 27,879 messages through 2026-08-28, channel 2180077318 verified"
    - "Full-parser replay on the backup: 100% location coverage for 2026-05..2026-08 candidates (158/158, 99/99, 145/145, 94/94); exactly 17 canonical district values, zero case/typo variants"
    - "Candidate replay (disposable PostGIS, real wef-import persist of all 27,886 messages): 2,524 July+ raw events landed; 88 deliberately staled offers re-derived by wef-replay-parser in one pass (stale_after_replay=0); second run reprocessed 0 (idempotent)"
    - "Candidate metrics: 3,055 offers all parser_version e2-v5; sentinel pin count 0; 3,012/3,055 offers on real locations, remainder ungeocoded off-map; zero implausible price magnitudes (the single sub-100k PLN price is a legitimate 14,000 zł/month rental, message 28768)"
    - "Production promotion: Release and deploy production run 33280067325 completed successfully on main after PR #210, activating the e2-v5 parser, migration chain 0012->0013->0014, raw archive, and replay command"
    - "Host-side operator follow-ups (routine operations, not epic gates): run wef-replay-parser on the production host to re-point historical sentinel/stale rows, then the geocode stage for newly resolved locations under ADR-021 budgets, then wef-accept-pending-geocode-pins"
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---


# E17-T6: Owner backup replay and production promotion

## Outcome

The owner supplies a fresh Telegram data backup; that backup is replayed through the
completed E17 pipeline into a production candidate, quality is verified against the
epic's acceptance metrics, and the release is promoted to production. This task is
the epic's completion gate: **E17 is not `done` until this promotion is recorded.**

## Scope

- Owner gate (explicit prerequisite, not automatable): the owner stages a new
  Telegram data backup and authorizes its use.
- Import the backup through the raw archive (and/or the historical export path) into
  a non-public production candidate under ADR-008 immutable-release rules; run the
  E17-T2 replay to convergence; run the geocode stage within ADR-021 budgets.
- Verified quality metrics on the candidate, recorded redacted:
  - location coverage for current-template candidates at or above the `e2-v4`+
    replay level (2026-07/08 export evidence: 145/145 and 27/27);
  - zero mixed-case or duplicate district facets (canonical vocabulary only);
  - `злотых`-style amounts stored at correct magnitude and currency;
  - no offer pinned to the `Unknown location` sentinel.
- Production promotion via the existing release workflow with health checks, then
  completion evidence recorded in the epic README (mirroring the E15/E16 production
  completion records).

## Out of scope

- Changes to production topology, TLS, or backup infrastructure (E7/E14 remain
  governing).
- Any parser/facet code changes discovered late — those spawn follow-up tasks, and
  this gate re-runs.

## Work

- The backup never enters Git or image layers; it is mounted read-only for the
  importer exactly like today's export staging.

## Acceptance criteria

- [ ] The owner's new backup is imported and replayed to convergence with zero
      unprocessed raw events remaining.
- [ ] All quality metrics above are evidenced in a redacted report linked from the
      epic README.
- [ ] Production promotion completes with the standard health/verification workflow,
      and the epic README records `done` with promotion evidence.
- [ ] Rollback/recovery instructions for the promotion exist and were rehearsed per
      deployment governance.

## Dependencies and gates

- E17-T1 through E17-T5 all completed.
- Owner action (backup provision + promotion authorization) is a hard gate.

## Risks and notes

- Backup size vs geocode quota and NUC capacity — budget pauses and resumability are
  the mitigation; do not disable them to meet a date.
- If quality metrics fail, the gate fails: fix forward through the owning task and
  re-run; never waive the metrics.

## Promotion checklist

- [ ] The epic spike is explicitly owner-approved for its current revision.
- [ ] Scope, acceptance, dependencies, priority, size, and traceability match the
      approved spike.
- [ ] Required deferred decisions are resolved.
- [ ] The file will be moved—not copied—to the epic's `tasks/`.
- [ ] Promotion metadata will identify the target, promoter, and timestamp.
