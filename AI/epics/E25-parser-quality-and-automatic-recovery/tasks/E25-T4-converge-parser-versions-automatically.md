---
schema: ai-workflow/task@1
id: E25-T4
epic: E25
title: "Converge parser versions and field provenance automatically"
status: draft
revision: 1
priority: P1
size: L
milestone: M5
dependencies: [E24-T1, E25-T2, E25-T3]
requirement_ids: [P-002, P-003, P-006, P-007]
decision_ids: [ADR-003, ADR-006, ADR-012]
deferred_decision_ids: []
promotion:
  source: ../proposed-tasks/E25-T4-converge-parser-versions-automatically.md
  promoted_by: Codex
  promoted_at: "2026-09-05T10:15:52Z"
spike_gate:
  status: invalidated
  file: ../SPIKE.md
  approved_revision: 1
  verified_by: Codex
  verified_at: "2026-09-05T10:15:52Z"
implementation_gate:
  status: invalidated
  file: ../IMPLEMENTATION_PLAN.md
  approved_revision: 1
  verified_by: Codex
  verified_at: "2026-09-05T10:22:44Z"
dependency_gate:
  status: blocked
  verified_by: null
  verified_at: null
  evidence: []
branch:
  required: true
  name: null
  task_id: E25-T4
  one_task_only: true
  created_at: null
  pull_request: null
completion:
  completed_by: null
  completed_at: null
  pull_request: null
  evidence: []
invalidation:
  invalidated_by: Codex
  invalidated_at: "2026-09-05T11:12:47Z"
  reason: "Groq Batch application-state retention conflicts with the required Zero Data Retention boundary; review queued synchronous transport."
  return_to: spike

---

# E25-T4: Converge parser versions and field provenance automatically

## Outcome

Deploying an accepted parser/policy version automatically repairs eligible historical records and closes their issues with stable identities and correct provenance.

## Scope and work

Schedule bounded version-aware replay after release, keep parser and source revision identities separate, refresh extraction/field provenance, preserve protected values, and reconcile issue/offer/filter changes.

Relevant seams are listed in the [epic spike](../SPIKE.md#research-method-and-evidence). The [audit](../../../audits/2026-09-05-system-audit.md) supplies the verified baseline and distinguishes source-confirmed risks from production observations.

## Acceptance criteria

- [ ] A release with a new parser version discovers stale eligible records automatically; a second run on unchanged source/version produces zero canonical changes.
- [ ] Every updated field traces to the current parser version and source evidence even when the source revision was unchanged; offer-source provenance cannot silently remain on the old extractor.
- [ ] Offer IDs, favorites, source links, contacts, deleted/hidden state, owner-verified values, and AI field protection survive replay; source edits cannot be overwritten by stale work.
- [ ] Replay reports considered, source-absent, updated, deferred, protected-conflict, and failed populations with a balanced denominator; version distributions converge for eligible rows.
- [ ] Historical replay yields to live ingestion under bounded resource/provider budgets, resumes after restart, and needs no routine backfill dispatch.

## Tests and verification

Database integration tests cover parser-only revision changes, current-source revision races, idempotency, protected origin conflicts, stable offer identity, and catalog facet/filter consistency.

Run affected format/lint/type/test/contract checks, the [definition of done](../../../workflow/DEFINITION_OF_DONE.md), and `make lint` / `make test` before a push. Record exact commands and outcomes in the task PR. Use synthetic/sanitized fixtures and real persistence boundaries where the failure crosses transactions; no production fault injection is assumed.

## Dependencies and gates

Required task dependencies: E24-T1, E25-T2, E25-T3. Their completed or valid stacked state must be proven before implementation begins; all must be done before completion/merge.

This promoted task remains `draft` under the [workflow](../../../workflow/README.md). [Implementation plan revision 1](../IMPLEMENTATION_PLAN.md) is approved; the task must satisfy its dependency and branch gates before implementation.

## Rollout and automatic operation

Requires E24-T1 before production replay. Use a small automatic canary cohort, validate value/provenance/visibility diffs, and expand in checkpointed batches.

Normal successful work, contention/transient retry, and restart recovery must require no per-record owner action. Escalate only an unresolved material ambiguity, protected-value conflict, repeated systemic/access failure, or destructive recovery decision after the bounded automatic path has been exhausted.

## Rollback and recovery

Pause scheduling, preserve the release/version ledger, and restore only changed fields whose origins still match the reverted replay; do not restore whole production tables.

## Risks and exclusions

Some legacy/operator/synthetic records are intentionally excluded from deterministic replay. Exclusions must be explicit and countable rather than preventing completion indefinitely.

Do not add production dependencies without owner approval, commit raw source/credentials, or mix unrelated refactoring into this task. General E14 infrastructure remains authoritative outside this task's specific regression/behavior scope.

## Readiness and completion

- [x] Spike revision 1 approval and task promotion are recorded; the authoritative file is under `tasks/`.
- [x] Implementation plan revision 1 is explicitly approved and the implementation gate is satisfied.
- [ ] Required dependencies are done, or valid ancestor PRs are recorded in a stacked gate.
- [ ] This task passes through `ready` and starts on its own dedicated branch/PR.
- [ ] Acceptance criteria, required checks, and the global definition of done pass; completion evidence is recorded.

The documentation branch is not this task's implementation branch. Follow the task-specific modules, migration ownership, numeric limits, and verification requirements in [implementation plan revision 1](../IMPLEMENTATION_PLAN.md). Acceptance criteria above are preserved from proposed revision 1; promotion adds workflow metadata without changing their scope.

## Provider revision gate

Spike and implementation plan revision 2 await owner approval following the
[Batch/ZDR incompatibility](../PROVIDER_PRIVACY_REVISION.md). Prior test evidence
is retained; no non-done task gate is restored implicitly.
