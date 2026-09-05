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

## Approval and implementation state

Revision 1 approvals are retained in AD-051/AD-052. Spike and implementation plan
revision 2 are owner-approved, including the [provider privacy amendment](PROVIDER_PRIVACY_REVISION.md).
Approval gates are restored to revision 2; dependency and task branch gates remain enforceable.

- Planning PR [327](https://github.com/Flippylolz/WEF/pull/327): all five required CI checks passed.
- T1 PR [328](https://github.com/Flippylolz/WEF/pull/328): published, 827 backend and 169 frontend tests passed locally.
- T2 PR [330](https://github.com/Flippylolz/WEF/pull/330): published, 852 backend and 169 frontend tests passed locally; 75-case benchmark has zero field failures.
- T3 draft PR [335](https://github.com/Flippylolz/WEF/pull/335) implements durable reservations, scheduled recovery and calibrated source validation under approved revision 2. [Implementation evidence](E25-T3-IMPLEMENTATION_EVIDENCE.md) records validation and remaining rollout gates.
- T4 cannot start without E24-T1, T2 and T3 dependency evidence. E24-T1 PR [331](https://github.com/Flippylolz/WEF/pull/331) is now open, but is not an ancestor of this E25 stack.

No merge, historical canonical application or provider activation has occurred.
The provider revision does not change T1/T2 extraction behavior or invalidate their
measured test results. Stacked PRs need required CI after retargeting to main.

## Scope and completion

Retain the backend-authoritative modular architecture, current dependency constraints, contact protections, and existing review/deployment safeguards. All task acceptance criteria and the [definition of done](../../workflow/DEFINITION_OF_DONE.md) must pass before completion.

E14 retains shared test infrastructure, general refactoring, capacity, and platform observability. E8 retains passive-event acceptance; E7-T5/E14-T9 retain backup and restore scope. No duplicate authoritative definitions are introduced.
