---
schema: ai-workflow/spike@1
epic: E0
title: Replace with spike title
status: draft
revision: 1
owner: owner
research_only: true
code_allowed: false
decision_ids: []
domain_docs: []
proposed_task_ids: []
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

# Spike: Replace with title

> Copy this file to an epic’s `SPIKE.md`. Replace example identity values before requesting approval. Keep `research_only: true` and `code_allowed: false` in every state.

## Question

State the bounded question this spike must answer.

## Context and constraints

- Link governing decisions, product requirements, contracts, architecture, security, ingestion, operations, governance, data evidence, and deferred gates.
- State assumptions, exclusions, time/research limits, and accepted constraints.

## Research method

Describe documentation review, existing-code/data inspection, calculations, and external references. Outputs must remain non-executable documentation.

Prohibited before implementation-plan approval:

- production or application code;
- scaffolds, migrations, infrastructure/configuration changes, or generated executable artifacts;
- throwaway scripts, prototypes, proof branches, or disposable proof code.

## Evidence

Record findings with direct references and distinguish verified facts, assumptions, and uncertainty.

## Options considered

For each viable option, document benefits, costs, risks, constraints, and reason for selection/rejection.

## Recommendation

State one recommendation and its consequences. Identify decisions that must be added, superseded, or resolved.

## Proposed task boundaries

List candidate task IDs and boundaries for refinement under `proposed-tasks/`. These remain non-actionable until promoted after spike approval.

## Risks and open questions

List unresolved issues, owners, and the decision or evidence required to close each one.

## Invalidation triggers

List epic-specific changes that would invalidate this recommendation in addition to the global workflow rules.

## Exit checklist

- [ ] The question is answered within the stated scope.
- [ ] Evidence and uncertainty are distinguishable.
- [ ] Affected decisions and domain documents are linked.
- [ ] Proposed task boundaries and dependencies are identified.
- [ ] No production or disposable proof code was created.
- [ ] `revision` represents the material content being submitted.
- [ ] `status` is `awaiting_approval` and approval remains `pending`.

## Owner decision

The owner records the decision only in the YAML `approval` object. Approval of this spike revision permits task refinement/promotion and implementation planning; it does not permit code.
