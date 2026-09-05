---
schema: ai-workflow/spike@1
epic: E24
title: "Automatic ingestion recovery"
status: awaiting_approval
revision: 1
owner: owner
research_only: true
code_allowed: false
decision_ids: [ADR-003, ADR-005, ADR-006, ADR-007, ADR-012, ADR-015]
domain_docs:
  - AI/ingestion/PIPELINE.md
  - AI/operations/DEPLOYMENT.md
proposed_task_ids: [E24-T1, E24-T2, E24-T3, E24-T4]
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

# Spike: Automatic ingestion recovery

## Question

How can ingestion terminate archived work, maintain a monotonic source cursor, and recover dependent media without an operator repeatedly running repair commands?

## Context and constraints

New, edited, and deleted source messages converge into the catalog with durable archive and media completion. Routine contention, restarts, and transient failures recover automatically, and health measures progress rather than repeated work.

The owner selected this audit and requested minimal manual operation on 2026-09-05. Routine human approvals/actions are not the product recovery mechanism. Existing [repository governance](../../governance/REPOSITORY_RULES.md) and [delivery workflow](../../workflow/README.md) still govern implementation revisions and releases. No new production dependency, provider spend increase, destructive data repair, or topology change is implicitly approved.

Affected domain documentation:
- [AI/ingestion/PIPELINE.md](../../../AI/ingestion/PIPELINE.md)
- [AI/operations/DEPLOYMENT.md](../../../AI/operations/DEPLOYMENT.md)

## Research method and evidence

Reviewed current `main` at `9fc612fc77dd752bc936bcc6cf8c6a13fe7d22b6`, existing tests, and repository workflow/architecture documentation. Ran locked validation suites and inspected bounded read-only production/GitHub evidence. The [audit](../../audits/2026-09-05-system-audit.md) records command results and separates confirmed behavior from hypotheses.

Audit I1 confirms a replay identity mismatch: 27,656 eligible pending rows, 25 pending rows with alternate-checksum terminal siblings, and sampled copies processed over 20,000 times. I2 records inconsistent durable/runtime cursors and lock-contention failures. I3 identifies a media retry gap after canonical commit. Production containers were healthy despite this evidence.

Primary implementation seams:
- [apps/backend/src/wef_backend/features/ingestion/application/raw_archive.py](../../../apps/backend/src/wef_backend/features/ingestion/application/raw_archive.py)
- [apps/backend/src/wef_backend/features/ingestion/application/telegram_events.py](../../../apps/backend/src/wef_backend/features/ingestion/application/telegram_events.py)
- [apps/backend/src/wef_backend/features/ingestion/infrastructure/raw_event_archive.py](../../../apps/backend/src/wef_backend/features/ingestion/infrastructure/raw_event_archive.py)
- [apps/backend/src/wef_backend/features/ingestion/application/telegram_reconciliation.py](../../../apps/backend/src/wef_backend/features/ingestion/application/telegram_reconciliation.py)
- [apps/backend/src/wef_backend/features/ingestion/application/live_media.py](../../../apps/backend/src/wef_backend/features/ingestion/application/live_media.py)

## Options considered

Leaving the current drainer and adding more retries would repeat the same checksum mismatch. A new external message broker would not fix acknowledgement semantics and would add an unapproved dependency. Manual replay can be an emergency tool but cannot be the normal completion mechanism.

## Recommendation

Keep the current PostgreSQL-backed design. Acknowledge the original archived event, preserve its immutable payload identity, establish a channel cursor independent of individual run finish order, and track media completion separately. Defer contention automatically; measure queue age and unique completions. Repair existing rows only after the identity fix has regression coverage.

The task files define proposed acceptance and rollout boundaries, not approval to implement. Policy, contract, migration, retry, and budget choices must be locked in the implementation plan after this spike is approved.

## Proposed task boundaries

- [E24-T1: Terminate original archive work and repair starvation](proposed-tasks/E24-T1-terminate-original-archive-work.md) — P1/L; dependencies: none.
- [E24-T2: Make source cursors monotonic and retries fair](proposed-tasks/E24-T2-monotonic-cursors-and-fair-retries.md) — P1/L; dependencies: E24-T1.
- [E24-T3: Recover media independently after message commit](proposed-tasks/E24-T3-recover-media-after-message-commit.md) — P1/L; dependencies: E24-T1.
- [E24-T4: Verify ingestion progress and automate recovery escalation](proposed-tasks/E24-T4-verify-progress-and-automate-recovery.md) — P1/M; dependencies: E24-T1, E24-T2, E24-T3.

## Risks and open questions

Reconstructed historical payloads must not replace richer or newer source revisions. Completion must not skip genuine edits, deleted-source visibility rules, or media work. A connection failure can occur between canonical commit and acknowledgement; retries must converge. Historical pending counts include records that are already canonical and must not be treated as missing offers.

The implementer must resolve concrete schema/contract and accepted numeric budgets in the promoted task/plan revisions. Irreducible ambiguity, access loss, protected-field conflict, and destructive recovery are exceptional manual cases; transient errors and routine backlog work must resume automatically. Existing ADR-015 backup deferral remains unchanged.

## Invalidation triggers

Material changes to source semantics, geospatial confidence/precision claims, automatic write authority, schema/contracts, provider choice or cost, release trust boundaries, or the evidence supporting this recommendation return the spike to review. Task sequencing, test, rollout, or rollback changes follow implementation-plan revision rules after approval.

## Exit checklist

- [x] Bounded question answered with one recommendation.
- [x] Evidence and uncertainty distinguishable in the linked audit.
- [x] Affected modules/domain documents and decisions identified.
- [x] Proposed task scope, acceptance, dependencies, and exception handling recorded.
- [x] Outputs are documentation only; no production or disposable proof artifacts created.
- [x] Revision 1 is awaiting approval; decision metadata remains pending.

## Owner decision

Record an attributable owner decision for this exact revision using the YAML approval object and durable evidence. Approval permits task refinement/promotion and implementation planning, not production code by itself.
