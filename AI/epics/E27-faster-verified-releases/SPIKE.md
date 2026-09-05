---
schema: ai-workflow/spike@1
epic: E27
title: "Faster verified releases"
status: approved
revision: 1
owner: owner
research_only: true
code_allowed: false
decision_ids: [ADR-008, ADR-009, ADR-010, ADR-013, ADR-014, ADR-017, ADR-023]
domain_docs:
  - AI/operations/DEPLOYMENT.md
  - AI/governance/REPOSITORY_RULES.md
proposed_task_ids: [E27-T1, E27-T2, E27-T3]
approval:
  required_role: owner
  status: approved
  decided_by: owner
  decided_at: "2026-09-05T10:18:07Z"
  approved_revision: 1
  evidence: OWNER_DECISIONS.md
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# Spike: Faster verified releases

## Question

Which measured release stages can be shortened without weakening exact-SHA verification, production configuration controls, required checks, or health-gated rollback?

## Context and constraints

An ordinary merged PR automatically reaches a verified production release with visible stage timing, minimal duplicate work, safe serialized activation, and no routine second dispatch.

The owner selected this audit and requested minimal manual operation on 2026-09-05. Routine human approvals/actions are not the product recovery mechanism. Existing [repository governance](../../governance/REPOSITORY_RULES.md) and [delivery workflow](../../workflow/README.md) still govern implementation revisions and releases. No new production dependency, provider spend increase, destructive data repair, or topology change is implicitly approved.

Affected domain documentation:
- [AI/operations/DEPLOYMENT.md](../../../AI/operations/DEPLOYMENT.md)
- [AI/governance/REPOSITORY_RULES.md](../../../AI/governance/REPOSITORY_RULES.md)

## Research method and evidence

Reviewed current `main` at `9fc612fc77dd752bc936bcc6cf8c6a13fe7d22b6`, existing tests, and repository workflow/architecture documentation. Ran locked validation suites and inspected bounded read-only production/GitHub evidence. The [audit](../../audits/2026-09-05-system-audit.md) records command results and separates confirmed behavior from hypotheses.

Audit R1 measures three merged-PR releases at 9m31s, 10m36s, and 14m48s. Verification took 5m33s–7m05s while deploy jobs took 77–87 seconds; one waited 5m37s before starting. A manual duplicate took 20m31s. R2 confirms a successful verification/publish workflow can skip deployment because the SHA has no associated merged PR.

Primary implementation seams:
- [.github/workflows/ci.yml](../../../.github/workflows/ci.yml)
- [.github/workflows/deploy-production.yml](../../../.github/workflows/deploy-production.yml)
- [Makefile](../../../Makefile)
- [apps/backend/Dockerfile](../../../apps/backend/Dockerfile)
- [apps/web/Dockerfile](../../../apps/web/Dockerfile)
- [scripts/deploy/evaluate_deploy_gate.py](../../../scripts/deploy/evaluate_deploy_gate.py)
- [scripts/prove_release_workflow.py](../../../scripts/prove_release_workflow.py)

## Options considered

Removing tests or deploying PR-head artifacts as if they were the squash-merge SHA would weaken verification. More manual dispatches worsen shared-workflow queuing. Parallel activation is unsafe on the shared host. New self-hosted runners or delivery platforms are unnecessary until measured queue evidence justifies them.

## Recommendation

First make merge-to-production and per-stage outcomes measurable. Consolidate equivalent verification for the exact release SHA, run independent backend/frontend checks and builds concurrently with existing cache support, and scope serialization to production mutation. Preserve deployment eligibility and all health/rollback/configuration gates. Treat duplicate emergency requests idempotently.

The task files define proposed acceptance and rollout boundaries, not approval to implement. Policy, contract, migration, retry, and budget choices must be locked in the implementation plan after this spike is approved.

## Proposed task boundaries

- [E27-T1: Measure merge-to-production time and report release outcomes](tasks/E27-T1-measure-release-and-report-outcomes.md) — P1/M; dependencies: none.
- [E27-T2: Parallelize verified work and bound the deployment lock](tasks/E27-T2-parallelize-verification-and-bound-deploy-lock.md) — P1/L; dependencies: E27-T1.
- [E27-T3: Prove the release budget and unattended recovery](tasks/E27-T3-prove-release-budget-and-unattended-recovery.md) — P1/M; dependencies: E27-T2.

## Risks and open questions

PR heads and merge SHAs differ. Cached artifacts must prove source identity and complete checks; job splitting must not omit required script, contract, image, or security proofs. Workflow-level concurrency currently protects all production mutations. Preserve protection while shortening its scope and preventing an older candidate from activating after a newer release.

The implementer must resolve concrete schema/contract and accepted numeric budgets in the promoted task/plan revisions. Irreducible ambiguity, access loss, protected-field conflict, and destructive recovery are exceptional manual cases; transient errors and routine backlog work must resume automatically. Existing ADR-015 backup deferral remains unchanged.

## Invalidation triggers

Material changes to source semantics, geospatial confidence/precision claims, automatic write authority, schema/contracts, provider choice or cost, release trust boundaries, or the evidence supporting this recommendation return the spike to review. Task sequencing, test, rollout, or rollback changes follow implementation-plan revision rules after approval.

## Exit checklist

- [x] Bounded question answered with one recommendation.
- [x] Evidence and uncertainty distinguishable in the linked audit.
- [x] Affected modules/domain documents and decisions identified.
- [x] Proposed task scope, acceptance, dependencies, and exception handling recorded.
- [x] Outputs are documentation only; no production or disposable proof artifacts created.
- [x] Revision 1 is owner-approved; decision metadata links the session reply.

## Owner decision

The owner approved revision 1 with `continue` in direct response to the revision-specific approval question. See [the decision transcript](OWNER_DECISIONS.md). Approval permits task refinement/promotion and implementation planning, not production code by itself.
