---
schema: ai-workflow/task@1
id: E0-T1
epic: E0
title: "Review architecture and dependency proposal"
status: draft
revision: 1
priority: P0
size: M
milestone: M1
dependencies: [E1-T1]
requirement_ids: []
decision_ids: [ADR-012]
deferred_decision_ids: []
promotion:
  source: ../proposed-tasks/E0-T1-review-architecture-and-dependency-proposal.md
  promoted_by: "Cursor Agent (owner-authorized)"
  promoted_at: "2026-08-12T21:03:00Z"
spike_gate:
  status: satisfied
  file: ../SPIKE.md
  approved_revision: 2
  verified_by: "Cursor Agent"
  verified_at: "2026-08-12T21:03:00Z"
implementation_gate:
  status: satisfied
  file: ../IMPLEMENTATION_PLAN.md
  approved_revision: 2
  verified_by: "Cursor Agent"
  verified_at: "2026-08-12T21:03:00Z"
dependency_gate:
  status: blocked
  verified_by: null
  verified_at: null
  evidence: []
branch:
  required: true
  name: null
  task_id: E0-T1
  one_task_only: true
  created_at: null
  pull_request: null
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

# E0-T1: Review architecture and dependency proposal

> Promoted after explicit owner approval of E0 spike revision 2. This task remains `draft`; no implementation or task branch is authorized until the current implementation plan is approved.

## Outcome

Record the independently reviewable architecture/dependency baseline that constrains the synthetic proof and later application scaffolding.

## Scope

- Review the approved [architecture/dependency spike](../SPIKE.md): backend/frontend ownership, SOLID/DRY rules, package-by-feature boundaries, interactors, presenters, service objects, ports/adapters, transactions, dependency inventory, and bootstrap boundaries.
- Confirm that [ADR-012](../../../decisions/adr/ADR-012-backend-centric-modular-monolith.md), affected contracts, and domain documentation remain aligned with spike revision 2.
- Record any approved correction as a new artifact revision and apply workflow invalidation when it changes material architecture.

## Out of scope

- Application code, manifests, lockfiles, Dockerfiles, Compose configuration, Make targets, migrations, or generated contracts.
- Running the E0-T2 proof.
- Implementing E1 repository or application scaffolding.

## Affected modules and contracts

- [Architecture](../../../architecture/README.md)
- [Contracts](../../../contracts/README.md)
- [Decision registry](../../../decisions/README.md)
- [Workflow](../../../workflow/README.md)

No runtime module, public API, or persisted contract changes are expected.

## Implementation notes

This is a documentation/review task. The owner-approved spike is the baseline; this task records review evidence and consistency checks rather than silently changing that baseline.

E1-T1 must initialize the safe repository and dedicated-branch capability before this task starts. This bootstrap dependency resolves the otherwise impossible requirement to put the first pre-repository review task on its own branch.

## Acceptance criteria

- [ ] Backend/frontend responsibilities and every layer's allowed dependencies are explicit and internally consistent.
- [ ] Adopted, evaluated, deferred, and rejected dependency categories have reasons and replacement paths.
- [ ] Repository, Dockerfile, Compose, Makefile, README, task-ownership, and branch boundaries are explicit.
- [ ] ADR-012 and affected architecture/contracts either match spike revision 2 or are updated through an approved material revision.
- [ ] Review evidence is attached without claiming that E0-T2 or product scaffolding has run.

## Test plan

- Documentation: validate YAML, relative links, task/decision IDs, and revision references.
- Architecture: compare dependency-direction and module-boundary statements across the spike, ADR-012, and architecture docs.
- Security/operations: verify source-data, secret, image-context, and branch gates remain explicit.

## Rollout and rollback

There is no runtime rollout. A material correction increments the spike or implementation-plan revision and follows invalidation/reapproval; a link-only correction does not.

## Ready checklist

- [x] The file is authoritative under `tasks/`; the proposed definition is removed during this promotion.
- [x] Promotion source, promoter, and timestamp are recorded.
- [x] `spike_gate` references owner-approved spike revision 2 and is `satisfied`.
- [x] `implementation_gate` references owner-approved implementation-plan revision 2 and is `satisfied`.
- [ ] E1-T1 is `done`, with dependency evidence recorded.
- [ ] Scope and acceptance criteria match the approved plan.

## Start checklist

- [ ] Status passed through `ready`.
- [ ] One new branch contains `E0-T1`.
- [ ] The branch and pull request contain this task only.
- [ ] `branch.name` and `branch.created_at` are recorded before setting `in_progress`.

## Done checklist

- [ ] Acceptance criteria pass.
- [ ] The global [definition of done](../../../workflow/DEFINITION_OF_DONE.md) passes.
- [ ] Completion actor, time, pull request, and evidence are recorded.
