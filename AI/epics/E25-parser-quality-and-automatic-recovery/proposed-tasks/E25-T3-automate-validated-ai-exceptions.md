---
schema: ai-workflow/proposed-task@1
id: E25-T3
epic: E25
title: "Automate validated AI exceptions under durable budgets"
status: proposed
revision: 1
actionable: false
priority: P1
size: L
milestone: M5
dependencies: [E25-T1]
requirement_ids: [P-002, P-003, P-006, P-007]
decision_ids: [ADR-003, ADR-006, ADR-012]
deferred_decision_ids: []
source: "owner-requested-system-audit:2026-09-05"
promotion:
  status: not_promoted
  target: null
  promoted_by: null
  promoted_at: null
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

This candidate remains non-actionable under the [workflow](../../../workflow/README.md). It must move rather than copy to `tasks/`, retain its ID, and receive complete promotion and gate metadata.

## Rollout and automatic operation

Start in automatic generate-and-validate observation mode, compare benchmark outcomes, then enable validated auto-apply for the accepted field allowlist and budget.

Normal successful work, contention/transient retry, and restart recovery must require no per-record owner action. Escalate only an unresolved material ambiguity, protected-value conflict, repeated systemic/access failure, or destructive recovery decision after the bounded automatic path has been exhausted.

## Rollback and recovery

Disable new auto-application while retaining queued proposals and audit events; revert only still-owned unchanged automatic fields through existing provenance-aware mechanisms.

## Risks and exclusions

The provider configuration and existing AI contract need explicit current-version review before changing owner-only behavior. No background self-training or automatic parser-code modification is included.

Do not add production dependencies without owner approval, commit raw source/credentials, or mix unrelated refactoring into this task. General E14 infrastructure remains authoritative outside this task's specific regression/behavior scope.

## Promotion checklist

- [ ] Current epic spike revision explicitly approved.
- [ ] Scope, acceptance, dependencies, tests, risks, rollout, and rollback reviewed against that revision.
- [ ] All referenced dependencies and required decisions resolved for the planned sequence.
- [ ] File moved, not copied, into `tasks/` with attributable promotion metadata.
- [ ] Dedicated branch and PR will cover this task only after implementation gates clear.
