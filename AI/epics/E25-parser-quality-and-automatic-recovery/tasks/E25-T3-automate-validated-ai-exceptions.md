---
schema: ai-workflow/task@1
id: E25-T3
epic: E25
title: "Automate validated AI exceptions under durable budgets"
status: in_progress
revision: 2
priority: P1
size: L
milestone: M5
dependencies: [E25-T1]
requirement_ids: [P-002, P-003, P-006, P-007]
decision_ids: [ADR-003, ADR-006, ADR-012]
deferred_decision_ids: []
promotion:
  source: ../proposed-tasks/E25-T3-automate-validated-ai-exceptions.md
  promoted_by: Codex
  promoted_at: "2026-09-05T10:15:52Z"
spike_gate:
  status: satisfied
  file: ../SPIKE.md
  approved_revision: 2
  verified_by: Codex
  verified_at: "2026-09-05T11:18:50Z"
implementation_gate:
  status: satisfied
  file: ../IMPLEMENTATION_PLAN.md
  approved_revision: 2
  verified_by: Codex
  verified_at: "2026-09-05T11:18:50Z"
dependency_gate:
  status: stacked
  verified_by: Codex
  verified_at: "2026-09-05T11:17:46Z"
  evidence:
    - task_id: E25-T1
      branch: feat/E25-T1-evidence-classification
      pull_request: https://github.com/Flippylolz/WEF/pull/328
      head_commit: 44eff1a
branch:
  required: true
  name: feat/E25-T3-durable-ai-recovery
  task_id: E25-T3
  one_task_only: true
  created_at: "2026-09-05T11:11:18Z"
  pull_request: https://github.com/Flippylolz/WEF/pull/335
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

# E25-T3: Automate validated AI exceptions under durable budgets

## Outcome

Routine parser exceptions are recovered automatically when source evidence validates the result; ambiguous records produce rare actionable exceptions.

## Scope and work

Turn existing owner-triggered proposal/batch capabilities into bounded scheduled recovery for eligible unique source revisions. Reuse privacy, model-provider, revision, and field-origin controls; add durable quota/backoff/deduplication without a new production dependency.

Relevant seams are listed in the [epic spike](../SPIKE.md#research-method-and-evidence). The [audit](../../../audits/2026-09-05-system-audit.md) supplies the verified baseline and distinguishes source-confirmed risks from production observations.

## Acceptance criteria

- [ ] Only T1-eligible records with repairable missing fields are queued; already-resolved, irrelevant, and genuinely source-absent fields do not trigger repeated AI calls.
- [ ] Auto-application requires field-level source spans, valid currency/unit/enum semantics, calibrated quality on the benchmark, and a current source revision; model confidence alone cannot authorize a write.
- [ ] Timeouts and rate limits persist a next-eligible time and resume automatically after restart without duplicate proposals/offers or quota bursts.
- [ ] Known deterministic or owner-verified values are preserved; protected conflicts, unsupported inference, and irreducible ambiguity stay unapplied with one minimized exception record.
- [ ] In a representative acceptance window, all objectively eligible routine cases complete without per-offer owner actions; report the eligibility denominator, unresolved reasons, provider spend, and human-intervention count.

## Tests and verification

Use deterministic provider fakes for timeout, 429, malformed JSON, fabricated evidence, stale revision, conflicting field, retry/restart, and idempotent apply cases. Confirm masked prompts and no raw provider response in public artifacts.

Run affected format/lint/type/test/contract checks, the [definition of done](../../../workflow/DEFINITION_OF_DONE.md), and `make lint` / `make test` before a push. Record exact commands and outcomes in the task PR. Use synthetic/sanitized fixtures and real persistence boundaries where the failure crosses transactions; no production fault injection is assumed.

## Dependencies and gates

Required task dependencies: E25-T1. Their completed or valid stacked state must be proven before implementation begins; all must be done before completion/merge.

This task is `in_progress` after readiness commit `6b1a5b8` under the [workflow](../../../workflow/README.md). [Implementation plan revision 2](../IMPLEMENTATION_PLAN.md) is approved; the task must satisfy its dependency and branch gates before implementation.

## Rollout and automatic operation

Start in automatic generate-and-validate observation mode, compare benchmark outcomes, then enable validated auto-apply for the accepted field allowlist and budget.

Normal successful work, contention/transient retry, and restart recovery must require no per-record owner action. Escalate only an unresolved material ambiguity, protected-value conflict, repeated systemic/access failure, or destructive recovery decision after the bounded automatic path has been exhausted.

## Rollback and recovery

Disable new auto-application while retaining queued proposals and audit events; revert only still-owned unchanged automatic fields through existing provenance-aware mechanisms.

## Risks and exclusions

The provider configuration and existing AI contract need explicit current-version review before changing owner-only behavior. No background self-training or automatic parser-code modification is included.

Do not add production dependencies without owner approval, commit raw source/credentials, or mix unrelated refactoring into this task. General E14 infrastructure remains authoritative outside this task's specific regression/behavior scope.

## Readiness and completion

- [x] Spike revision 1 approval and task promotion are recorded; the authoritative file is under `tasks/`.
- [x] Implementation plan revision 2 is explicitly approved and the implementation gate is satisfied.
- [x] Required dependencies are done, or valid ancestor PRs are recorded in a stacked gate.
- [x] This task passes through `ready` and starts on its own dedicated branch/PR.
- [ ] Acceptance criteria, required checks, and the global definition of done pass; completion evidence is recorded.

The documentation branch is not this task's implementation branch. Follow the task-specific modules, migration ownership, numeric limits, and verification requirements in [implementation plan revision 2](../IMPLEMENTATION_PLAN.md). Acceptance criteria above are preserved from proposed revision 1; promotion adds workflow metadata without changing their scope.

## Provider revision gate

Spike and implementation plan revision 2 are explicitly owner-approved following the
[Batch/ZDR incompatibility](../PROVIDER_PRIVACY_REVISION.md). Prior test evidence
is retained; approval gates are restored explicitly to revision 2.

Revision 2 changes the transport to durable single-item inference under ZDR,
including owner cohort entry points sharing its quota. Acceptance criteria and
field authority are retained; the exact state/retry amendment is linked above.

Revision 2 restored to ready after explicit owner approval. Original readiness
commit a9f24f1 and invalidation commit 1448cea remain in history.

## Local implementation evidence

See [T3 implementation evidence](../E25-T3-IMPLEMENTATION_EVIDENCE.md) for passing
local checks, changed files and outstanding live acceptance/dependency gates.
