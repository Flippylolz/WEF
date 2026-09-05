---
schema: ai-workflow/epic@1
id: E25
title: "Parser quality and automatic recovery"
status: in_progress
milestones: [M5]
owner: owner
spike: SPIKE.md
implementation_plan: IMPLEMENTATION_PLAN.md
---

# E25: Parser quality and automatic recovery

## Outcome

Structured offer fields reflect source evidence, parser improvements converge existing records automatically, and AI handles bounded validated exceptions without routine owner review.

## Audit basis

Audit P1 reproduces the Ostrzycka missing price and included-storage fields with current e2-v13. P2 shows non-candidates are all labeled parser_miss, while some silent omissions are not classified. P3 records 3,294 e2-v11 offers versus five e2-v13 offers and owner-triggered AI recovery. Visible-field absence is a baseline, not an accuracy score.

See the [5 September system audit](../../audits/2026-09-05-system-audit.md) for tests, production observations, source references, uncertainty, and the cross-epic sequence.

## Promoted tasks

- [E25-T1: Benchmark source evidence and classify repairable gaps](tasks/E25-T1-benchmark-source-evidence-and-triage.md) — P1/M; dependencies: none.
- [E25-T2: Repair deterministic field extraction and money semantics](tasks/E25-T2-repair-deterministic-extraction.md) — P1/M; dependencies: E25-T1.
- [E25-T3: Automate validated AI exceptions under durable budgets](tasks/E25-T3-automate-validated-ai-exceptions.md) — P1/L; dependencies: E25-T1.
- [E25-T4: Converge parser versions and field provenance automatically](tasks/E25-T4-converge-parser-versions-automatically.md) — P1/L; dependencies: E24-T1, E25-T2, E25-T3.

Each file defines one independently reviewable change, tests, acceptance evidence, rollout, rollback, and exceptional manual handling. Dependencies are task IDs and remain enforceable at promotion.

## Automation requirement

The owner requested as little manual work as possible, with manual work only in extreme cases. Routine processing must use durable, bounded automatic recovery. Measure eligible work completed and human interventions. Do not trade correctness or source evidence for a superficially empty queue.

## Approval state

- Owner approved [spike revision 1](SPIKE.md) on 2026-09-05; AD-047 records the session decision.
- All four tasks are promoted at revision 1; T1 is implemented and validated locally; T2 is implemented on a stack above T1; T3–T4 retain their dependency gates.
- [Implementation plan revision 1](IMPLEMENTATION_PLAN.md) is approved on 2026-09-05; AD-048 records the decision.
- E25-T1 has no task dependency. E25-T4 remains blocked on E24-T1 as well as E25-T2/T3; no prerequisite completion is assumed.
- Implementation is authorized within plan revision 1; production/provider prerequisites and merge authorization remain separate.

## Current implementation evidence

[E25-T1 evidence](E25-T1-IMPLEMENTATION_EVIDENCE.md) records the 75-case benchmark,
evaluation lifecycle, bounded classification backfill, eligibility selector,
validation results and changed-file inventory. Following explicit owner publication
approval, planning PR [327](https://github.com/Flippylolz/WEF/pull/327) and T1 PR
[328](https://github.com/Flippylolz/WEF/pull/328) are open.
[T2 evidence](E25-T2-IMPLEMENTATION_EVIDENCE.md) records deterministic extraction
repairs and regression validation. No merge, production repair or AI activation
has occurred.

## Scope and completion

Retain the backend-authoritative modular architecture, current dependency constraints, contact protections, and existing review/deployment safeguards. All task acceptance criteria and the [definition of done](../../workflow/DEFINITION_OF_DONE.md) must pass before completion.

E14 retains shared test infrastructure, general refactoring, capacity, and platform observability. E8 retains passive-event acceptance; E7-T5/E14-T9 retain backup and restore scope. No duplicate authoritative definitions are introduced.
