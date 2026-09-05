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

- Planning PR #338 merged as `9d095f1`; AD-053 records explicit merge and staged rollout authorization.
- T1 PR #328 is done on `ea47448`: healthy release and bounded classification acceptance.
- T2 PR #330 is done on `d9f5e30`: healthy e2-v14 release, zero benchmark field failures, and a read-only production comparison.
- T3 PR #335 is prepared against main; submission/application remain disabled pending activation prerequisites and live acceptance.
- T4 PR #337 has validated implementation, including 1,080 backend and 169 frontend tests; its T3 completion gate remains enforceable.

No E25 automatic historical canonical application or scheduled provider activation
has occurred. Read-only extraction differences are not safe-repair counts.

## Scope and completion

Retain the backend-authoritative modular architecture, current dependency constraints, contact protections, and existing review/deployment safeguards. All task acceptance criteria and the [definition of done](../../workflow/DEFINITION_OF_DONE.md) must pass before completion.

E14 retains shared test infrastructure, general refactoring, capacity, and platform observability. E8 retains passive-event acceptance; E7-T5/E14-T9 retain backup and restore scope. No duplicate authoritative definitions are introduced.
