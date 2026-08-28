---
schema: ai-workflow/task@1
id: E15-T3
epic: E15
title: "Recover the production gap and prove outage recovery"
status: in_progress
revision: 1
priority: P0
size: M
milestone: M4
dependencies: [E15-T1, E15-T2]
requirement_ids: [P-006, P-007]
decision_ids: [ADR-003, ADR-005, ADR-006, ADR-007, ADR-008, ADR-010, ADR-015]
deferred_decision_ids: []
promotion:
  source: ../proposed-tasks/E15-T3-recover-gap-and-prove-outage-recovery.md
  promoted_by: "Codex agent (owner-approved E15 planning under AD-039)"
  promoted_at: "2026-08-28T14:31:47Z"
spike_gate:
  status: satisfied
  file: ../SPIKE.md
  approved_revision: 1
  verified_by: "Codex agent (owner-approved E15 planning under AD-039)"
  verified_at: "2026-08-28T14:31:47Z"
implementation_gate:
  status: satisfied
  file: ../IMPLEMENTATION_PLAN.md
  approved_revision: 1
  verified_by: "Codex agent (owner-approved E15 implementation under AD-040)"
  verified_at: "2026-08-28T14:33:48Z"
dependency_gate:
  status: satisfied
  verified_by: "Codex agent (owner-approved E15 implementation under AD-040)"
  verified_at: "2026-08-28T20:39:49Z"
  evidence:
    - "E15-T1 done through green-CI PR #189; merge b4b3d6112f271633127d4002110ed0ba5924937e"
    - "E15-T2 done through green-CI PR #190; merge 7184cc2d67aafadc654c26fa26fd039ca4390ab2"
branch:
  required: true
  name: chore/E15-T3-production-recovery
  task_id: E15-T3
  one_task_only: true
  created_at: "2026-08-28T20:39:49Z"
  pull_request: "https://github.com/Flippylolz/WEF/pull/191"
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

# E15-T3: Recover the production gap and prove outage recovery

## Outcome

The missed production range is reconciled through the reviewed E15 controls, and
redacted production evidence proves live delivery, passive-event loss recovery,
disconnect/restart recovery, truthful health/alert behavior, and no source-message gap.

## Scope

- Deploy the approved E15-T1/T2 release through the existing immutable health-gated workflow.
- Run bounded reconciliation from checkpoint `29202` through the then-current verified
  remote head; do not hard-code `29257` as a terminal head if the channel advances.
- Verify source messages, revisions, candidate/offer outcomes, checkpoint alignment,
  geocode/media follow-up state, and public visibility consequences without logging source data.
- Exercise a safe missed-passive-event or paused-listener scenario, reconnect/restart,
  automatic catch-up, idempotent repeat, and alert fire/recovery.
- Update E8 operational acceptance, B-003, M4, deployment/runbook documentation, and
  incident evidence with redacted counts/IDs/timestamps and exact release/check results.

## Out of scope

- Manual visibility promotion without review, source-text publication, session rotation
  unless independently required, full historical import, backup claims, or unrelated E14 work.

## Work

- Define preflight/abort/rollback boundaries before any production mutation, including
  current release, source head, database checkpoint, worker ownership, and public health.
- Reconcile with the production command/path selected by the approved implementation
  plan and capture only bounded redacted evidence.
- Prove the worker self-heals after a controlled outage or deliberately suppressed
  passive event without operator data repair.
- Close or narrow B-003 and E8/M4 acceptance only to the extent the evidence supports.

## Acceptance criteria

- [x] The verified production database has no unexplained message-ID suffix gap from
  `29202` through the reconciliation run's recorded remote head.
- [x] Missed candidate messages produce the expected canonical offers/revisions or a
  documented parser/review outcome; no duplicate source, revision, offer, or contact row is created.
- [x] Repeating reconciliation changes no already-current canonical data and does not
  move the checkpoint backward.
- [x] A controlled disconnect/restart and a missed-passive-event scenario recover within
  the approved bound while public API readiness remains available.
- [x] Consumer/reconciliation failure makes worker health/alerting fail, and successful
  recovery clears the signal; Docker cannot report a dead pipeline as healthy.
- [x] Production logs/evidence contain no source text, contacts, credentials, sessions,
  raw payloads, or database secrets.
- [x] Public HTTPS/API health, AI Forecast isolation, database readiness, container
  limits, and rollback compatibility remain verified.
- [x] B-003, E8, M4, and operator runbooks record exact redacted release/check evidence
  and retain any unresolved edit/delete/media limitation honestly.

Exact redacted results, timestamps, counters, and limitations are recorded in
[E15 production recovery evidence](../PRODUCTION_EVIDENCE.md). The production acceptance
boundary is remote head `29335` on release `7184cc2d67a`; real passive new/edit/delete
callbacks and live media acquisition remain open under E8/M4 and are not claimed here.

## Affected modules and contracts

- Existing release/deploy, smoke, rollback, and worker-status commands provide the
  mutation and evidence paths; no ad-hoc production script or raw export is committed.
- `AI/operations/{DEPLOYMENT,BLOCKERS}.md`, E8 acceptance records, M4, and E15 workflow
  artifacts receive redacted exact release/checkpoint/rehearsal evidence.
- No public or persisted contract change is expected; any discovered need returns to
  the implementation-plan or spike gate before production mutation.

## Risks and notes

This task mutates production only through approved reconciliation and deployment paths.
It must not expose source data in reports or confuse persistence with backup. If the
remote source advances during verification, record a stable observation boundary and
reconcile again rather than declaring an ambiguous head complete.

## Test plan

- Preflight: deployed release, worker singleton, remote observed head, local checkpoint,
  database readiness, HTTPS/API health, Forecast isolation, rollback target, and log safety.
- Recovery: bounded reconciliation, stable observation boundary, canonical counts,
  idempotent repeat, no duplicate rows, and checkpoint monotonicity.
- Rehearsal: disconnect/restart, deliberately missed passive-event recovery, consumer/
  reconciliation health fire and clear, public-readiness independence.
- Documentation: record redacted exact commands/results; retain unsupported delete/media
  guarantees and backup deferral honestly.

## Rollout and rollback

E15-T1/T2 must be merged, green, automatically deployed, and health-verified before
recovery begins. Abort on unexpected worker ownership, source identity, checkpoint,
schema, health, or release state. Roll back through the immutable prior image if worker
health or reconciliation regresses; committed idempotent source recovery is retained and
must not be undone or checkpoint-rewound.

## Ready checklist

- [x] Authoritative under `tasks/`; the proposed definition was moved, not copied.
- [x] Promotion metadata and owner-approved spike revision 1 are recorded.
- [x] Implementation plan revision 1 is owner-approved and the gate is satisfied.
- [x] E15-T1 and E15-T2 are done with satisfied dependency evidence.
- [x] Scope and acceptance match the spike recommendation.
