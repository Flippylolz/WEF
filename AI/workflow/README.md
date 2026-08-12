# Approval-Gated Delivery Workflow

This workflow controls all epic work. Approval is revision-specific and attributable; file location, priority, an earlier review, or silence never grants permission to code.

## Mandatory lifecycle

1. **Select an epic.** Set its workspace status to `selected`.
2. **Research and document the spike.** Create/refine `SPIKE.md`; this phase is documentation and research only.
3. **Obtain explicit owner spike approval.** The owner approves the current `revision` in the spike front matter.
4. **Refine and promote proposed tasks.** Move approved candidates from `proposed-tasks/` to `tasks/` inside the same epic, preserving their stable IDs and recording promotion metadata.
5. **Write the implementation plan.** Sequence promoted tasks and document modules, tests, risks, migrations, rollout, and rollback.
6. **Obtain explicit owner implementation approval.** The owner approves the current implementation-plan `revision`.
7. **Implement task by task.** Satisfy the dependency gate, move one task to `ready`, create its dedicated branch, then move it to `in_progress`.

No production code, generated scaffold, executable experiment, migration, infrastructure change, or disposable proof code may be written before step 6 is complete. Spike work may inspect existing code/data and cite research, but its committed outputs are Markdown and other non-executable documentation only.

## Epic workspace

```text
AI/epics/E<id>-<slug>/
├── README.md
├── SPIKE.md
├── IMPLEMENTATION_PLAN.md
├── proposed-tasks/
│   └── E<id>-T<n>-<slug>.md
└── tasks/
    └── E<id>-T<n>-<slug>.md
```

`tasks/` is absent until the spike is approved and the first task is promoted. A task definition exists authoritatively in exactly one of `proposed-tasks/` or `tasks/`, never both.

## YAML conventions

All workflow artifacts begin with YAML front matter.

- `schema` is one of the exact versioned constants below.
- `revision` is an integer starting at `1`. Increment it for every material change.
- IDs match `E[0-9]+` for epics, `E[0-9]+-T[0-9]+` for tasks, `M[1-9][0-9]*` for milestones, `P-[0-9]{3}` for product requirements, `ADR-[0-9]{3}` for ADRs, and `D-[0-9]{3}` for deferred decisions.
- Times are quoted RFC 3339 UTC strings such as `"2026-08-12T20:00:00Z"`.
- Unknown/unset scalar values are YAML `null`, not empty strings or placeholders.
- ID/reference collections are arrays; use `[]` when empty.
- State values are lowercase exact enum values; do not invent synonyms.

## Epic README schema

Required fields:

```yaml
---
schema: ai-workflow/epic@1
id: E0
title: Architecture and dependency spike
status: draft
milestones: [M1]
owner: owner
spike: SPIKE.md
implementation_plan: IMPLEMENTATION_PLAN.md
---
```

`status` is exactly one of:

- `draft`: workspace is being assembled.
- `selected`: owner/team selected the epic; spike work may begin.
- `planning`: spike is approved and tasks/implementation plan are being refined, or implementation-plan approval is pending.
- `ready`: current spike and implementation-plan revisions are approved; individual tasks may qualify for `ready`.
- `in_progress`: at least one approved task is being implemented.
- `done`: all required tasks and epic acceptance evidence are done.
- `cancelled`: epic will not proceed.
- `deferred`: epic intentionally waits for a named trigger.

An epic cannot enter `ready` or `in_progress` unless both approval artifacts are valid for their current revisions.

## Approval schema

`SPIKE.md` and `IMPLEMENTATION_PLAN.md` use this exact object:

```yaml
approval:
  required_role: owner
  status: pending
  decided_by: null
  decided_at: null
  approved_revision: null
  evidence: null
```

Rules:

- `status` is exactly `pending`, `approved`, `rejected`, or `invalidated`.
- Only the repository/product owner may make the decision; `decided_by` records that attributable identity.
- `approved` requires non-null `decided_by`, `decided_at`, `approved_revision`, and `evidence`; `approved_revision` must equal the artifact’s current integer `revision`.
- `evidence` is an owner-authored durable reference, such as a pull-request review URL, issue/comment URL, or owner-signed approval record path. Review activity or a contributor-written claim is insufficient.
- `rejected` requires `decided_by`, `decided_at`, and `evidence`, while `approved_revision` remains `null`; revise the artifact, increment `revision`, and reset approval to `pending`.
- `pending` requires all four decision fields to be `null`.
- `invalidated` preserves the prior non-null decision fields and approved revision as historical context; the artifact’s incremented current `revision` no longer equals `approved_revision`, and every `invalidation` field is non-null.
- Approval of one artifact or revision never approves another artifact or revision.

Approval-bearing artifact states are exactly `draft`, `awaiting_approval`, `approved`, or `invalidated`:

- `draft` permits `approval.status: pending` or `rejected`.
- `awaiting_approval` requires `approval.status: pending`.
- `approved` requires `approval.status: approved` and matching revisions.
- `invalidated` requires `approval.status: invalidated`.

## Spike schema and gate

Use [the spike template](templates/SPIKE.md). Its required fields are:

- `schema: ai-workflow/spike@1`
- `epic`, `title`, `status`, and integer `revision`
- `research_only: true`
- `code_allowed: false`
- the exact `approval` and `invalidation` objects

Spike approval authorizes task refinement/promotion and implementation planning only. It never authorizes code.

## Proposed-task schema and states

Use [the proposed-task template](templates/PROPOSED_TASK.md). Its fields are:

- `schema: ai-workflow/proposed-task@1`
- `id`, `epic`, non-empty `title`, and integer `revision`; the task ID’s epic prefix must equal `epic`
- `status` from the enum below and constant `actionable: false`
- `priority: P0 | P1 | P2`, `size: S | M | L`, and one `milestone`
- unique `dependencies`, `requirement_ids`, `decision_ids`, and `deferred_decision_ids` arrays using the ID formats above
- nullable `source`, which records non-path source provenance when applicable
- `promotion.status: not_promoted` with null `target`, `promoted_by`, and `promoted_at`

`status` is exactly:

- `proposed`: candidate planning input.
- `cancelled`: intentionally removed, with rationale in the body.
- `deferred`: waits for a named trigger.

There is no `ready` or `in_progress` state in `proposed-tasks/`. Existing candidates there are not approved, scheduled, or actionable.

A proposed task may be promoted only when:

- its epic spike is `approved` for its current revision;
- its scope, acceptance criteria, dependencies, priority/size, and traceability have been reviewed against that spike;
- no required deferred decision is unresolved; and
- it is converted to the task schema while being moved—not copied—to `tasks/`; and
- the task’s `promotion.source`, `promoted_by`, and `promoted_at` record the proposed file and promotion event.

## Task schema, states, and gates

Use [the task template](templates/TASK.md). Its identity, priority, size, milestone, dependency, and traceability fields follow the proposed-task constraints. In addition:

- `schema` is exactly `ai-workflow/task@1`.
- `promotion` contains the prior proposed-task path plus non-null promoter identity and RFC 3339 promotion time.
- `spike_gate` and `implementation_gate` contain `status`, relative artifact `file`, integer `approved_revision`, verifier, and verification time.
- `dependency_gate` contains `status`, verifier, verification time, and an evidence array.
- `branch.required` and `branch.one_task_only` are always `true`; `branch.task_id` equals `id`.
- `completion` contains nullable actor/time/PR and an evidence array.
- `invalidation` uses the global object below.

A promoted task’s `status` is exactly:

- `draft`: promoted but not yet eligible.
- `ready`: all approvals are satisfied and dependencies are either complete or represented by a valid ordered stack for the current revisions.
- `in_progress`: `ready` gates remain valid and the dedicated branch is recorded.
- `done`: acceptance criteria and the [definition of done](DEFINITION_OF_DONE.md) are satisfied.
- `cancelled`: intentionally stopped by an approved scope decision.
- `deferred`: waits for a named trigger.
- `invalidated`: material upstream change requires revalidation before work resumes.

A task cannot enter `ready` or `in_progress` unless all of these are true:

1. `spike_gate.status` is `satisfied`, references the epic’s approved current spike revision, and records verifier/time.
2. The definition is under `tasks/` and has complete promotion metadata.
3. `implementation_gate.status` is `satisfied`, references the epic’s approved current implementation-plan revision, confirms that plan’s `task_sequence` contains this task ID and current task revision, and records verifier/time.
4. `dependency_gate.status` is `satisfied` or `stacked`. `satisfied` requires every dependency to be `done`; `stacked` requires every incomplete dependency to have an open ancestor pull request recorded in direct merge order.
5. Every referenced deferred decision is resolved or explicitly removed by a newly approved scope/plan revision.

Before `in_progress`, `branch.name` must be non-null, contain this task’s ID, and identify a branch used for no other task.

Gate `status` is exactly `blocked`, `stacked`, `satisfied`, or `invalidated`. `stacked` is valid only for `dependency_gate`; spike and implementation gates never use it. A `satisfied` spike/implementation gate requires non-null revision, verifier, and time; a `blocked` gate requires those fields to be `null`. An `invalidated` gate retains the previously verified revision/evidence for history and requires the task invalidation record.

## Dependency gate

- Dependencies are task IDs, not prose.
- No task may depend on itself or contain a dependency cycle. `cancelled`, `deferred`, `ready`, or `in_progress` never count as complete.
- An empty `dependencies: []` may use `dependency_gate.status: satisfied` with empty evidence after verifier/time are recorded.
- Otherwise, `dependency_gate.evidence` lists every dependency ID and the commit/PR/reference proving its `done` state.
- A satisfied dependency gate requires non-null verifier/time and evidence for every non-empty dependency. A blocked gate has null verifier/time and empty evidence.
- A stacked dependency gate requires non-null verifier/time and one evidence entry for every incomplete dependency, including task ID, branch, pull request URL, and head commit. Every dependency branch must be an ancestor of the current task branch in direct stack order.
- `stacked` permits implementation to continue but never permits `done`, merge, deployment, or use as completion evidence. Before completion, all dependencies must become `done` and the gate must transition to `satisfied`.
- If an upstream branch changes materially, refresh the descendant branch and evidence; invalidate the task when the approved scope or plan no longer matches.
- Any newly discovered dependency is a material plan/task change: stop, invalidate as required, update the plan, and reapprove before continuing.
- Removing a dependency requires an approved material revision; it cannot be bypassed by editing only the task gate.

## One branch per task

- Every implementation task uses exactly one dedicated branch and pull request.
- The branch name contains the task ID, for example `feature/E4-T1-map-geojson`, `fix/E3-T3-geocode-bounds`, or `spike/E0-T2-architecture-proof`.
- A branch/PR contains one task only; do not batch unrelated tasks or reuse a branch for a later task.
- Branch from the latest `main` when no dependency is open. For an ordered stack, branch from the immediate upstream task and target that branch so the pull request diff contains only the current task.
- Satisfy procedural review/CI governance, then merge/retarget from the base of the stack upward. Squash merge and delete each merged branch.
- Documentation-only spike/planning revisions may use a documentation branch, but that branch must contain no production or disposable proof code.

## Implementation-plan schema and gate

Use [the implementation-plan template](templates/IMPLEMENTATION_PLAN.md). Its required fields are:

- `schema: ai-workflow/implementation-plan@1`
- `epic`, `title`, `status`, and integer `revision`
- `spike_revision`, equal to the currently approved spike revision
- ordered `task_sequence` objects, each containing exactly one promoted task `id` and its current integer `revision`
- the exact `approval` and `invalidation` objects

Implementation approval authorizes only the recorded scope, task sequence, constraints, tests, migrations, risks, and rollout for that revision. Individual task and dependency gates still apply.

## Invalidation rules

Approval-bearing artifacts and promoted tasks use:

```yaml
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
```

While approval is valid, all four fields are `null`. On invalidation:

1. Stop affected implementation immediately.
2. Increment the materially changed artifact’s `revision`.
3. Set artifact `status: invalidated`. For a spike/plan, also set `approval.status: invalidated`; retain prior decision evidence in version history.
4. Fill every invalidation field. `return_to` is `spike` or `implementation_plan`.
5. Set affected `ready`/`in_progress` tasks to `invalidated` and their affected gates to `invalidated`.
6. Revise, move to `awaiting_approval`, and obtain new explicit owner approval before restoring downstream gates.

Return to the spike gate when a change materially affects product scope/acceptance, public or persisted contracts, architecture/dependency direction, security model, ingestion semantics, deployment topology/configuration ownership, or a spike premise/recommendation.

Return to the implementation-plan gate when the approved spike remains valid but task scope, task sequence, modules, dependencies, acceptance criteria, tests, migrations, risks, rollout, or rollback materially changes.

A spike invalidation automatically invalidates its implementation plan and every non-done task gate. An implementation-plan invalidation automatically invalidates every non-done task’s implementation gate. Completed tasks remain historical facts, but the reapproved plan must identify remediation or follow-up work.

Typographical, formatting, and link-only corrections that do not change meaning are non-material: they do not increment `revision` or invalidate approval.

## Templates and completion

- [Spike template](templates/SPIKE.md)
- [Proposed-task template](templates/PROPOSED_TASK.md)
- [Promoted task template](templates/TASK.md)
- [Implementation-plan template](templates/IMPLEMENTATION_PLAN.md)
- [Definition of done](DEFINITION_OF_DONE.md)
