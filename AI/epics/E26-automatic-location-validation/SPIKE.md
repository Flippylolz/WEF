---
schema: ai-workflow/spike@1
epic: E26
title: "Automatic location validation and repair"
status: approved
revision: 2
owner: owner
research_only: true
code_allowed: false
decision_ids: [ADR-003, ADR-005, ADR-012, ADR-021]
domain_docs:
  - AI/ingestion/PIPELINE.md
  - AI/data/QUALITY_AND_READINESS.md
  - AI/operations/OPERATOR_COMMANDS.md
proposed_task_ids: [E26-T1, E26-T2, E26-T3, E26-T4]
approval:
  required_role: owner
  status: approved
  decided_by: "Owner (Flippylolz), recorded by Codex"
  decided_at: "2026-09-06T15:24:20.540396+00:00"
  approved_revision: 2
  evidence: "OWNER_DECISION.md: municipal-first follow-up authorization"
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# Spike: Automatic location validation and repair

## Question

How can wrong street matches and coarse neighborhood points be prevented and repaired automatically without hiding listings or pretending a street-only source identifies a building?

## Context and constraints

Map positions agree with source addresses and expose their true precision. Routine wrong or stale geocodes are detected, re-resolved, and corrected automatically; owner involvement is reserved for material ambiguity and protected-value conflicts.

The owner selected this audit and requested minimal manual operation on 2026-09-05. Routine human approvals/actions are not the product recovery mechanism. Existing [repository governance](../../governance/REPOSITORY_RULES.md) and [delivery workflow](../../workflow/README.md) still govern implementation revisions and releases. No new production dependency, provider spend increase, destructive data repair, or topology change is implicitly approved.

Affected domain documentation:
- [AI/ingestion/PIPELINE.md](../../ingestion/PIPELINE.md)
- [AI/data/QUALITY_AND_READINESS.md](../../data/QUALITY_AND_READINESS.md)
- [AI/operations/OPERATOR_COMMANDS.md](../../operations/OPERATOR_COMMANDS.md)

## Research method and evidence

Reviewed current `main` at `9fc612fc77dd752bc936bcc6cf8c6a13fe7d22b6`, existing tests, and repository workflow/architecture documentation. Ran locked validation suites and inspected bounded read-only production/GitHub evidence. The [audit](../../audits/2026-09-05-system-audit.md) records command results and separates confirmed behavior from hypotheses.

Audit M1 identifies both owner-reported cases and an additional Jugosłowiańska result whose provider address is Grochowska town hall despite confidence 1.00. Coarse pending results are automatically accepted using historical manual_accept lineage. All three selected results use v1 query/request versions. M2 also reproduces Gocław being treated as a city in display normalization.

Primary implementation seams:
- [apps/backend/src/wef_backend/features/ingestion/domain/geocoding.py](../../../apps/backend/src/wef_backend/features/ingestion/domain/geocoding.py)
- [apps/backend/src/wef_backend/features/ingestion/infrastructure/geocoder_adapters.py](../../../apps/backend/src/wef_backend/features/ingestion/infrastructure/geocoder_adapters.py)
- [apps/backend/src/wef_backend/features/ingestion/infrastructure/accept_pending_geocode_pins_adapter.py](../../../apps/backend/src/wef_backend/features/ingestion/infrastructure/accept_pending_geocode_pins_adapter.py)
- [apps/backend/src/wef_backend/recurring_geocode_worker.py](../../../apps/backend/src/wef_backend/recurring_geocode_worker.py)
- [apps/web/src/components/warsaw-map.tsx](../../../apps/web/src/components/warsaw-map.tsx)

## Options considered

Manually moving every point conflicts with the owner's automation requirement. Raising a confidence threshold cannot reject the observed wrong-street result at 1.00. Hiding every uncertain offer would unnecessarily reduce discovery. Adding a provider alone cannot replace address-agreement checks and is not pre-approved.

## Recommendation

Use source/provider address agreement and geographic evidence before score thresholds, with versioned street/neighborhood/district normalization and bounded candidate retries. Supersede the recurring blanket coarse-pin acceptance behavior associated with AD-034. Automatically revalidate stale accepted results and apply unambiguous corrections; expose source-limited area/street precision honestly through the backend projection.

The task files define proposed acceptance and rollout boundaries, not approval to implement. Policy, contract, migration, retry, and budget choices must be locked in the implementation plan after this spike is approved.

## Proposed task boundaries

- [E26-T1: Validate address agreement and source-supported precision](tasks/E26-T1-validate-address-agreement-and-precision.md) — P1/L; dependencies: none.
- [E26-T2: Revalidate and repair existing points automatically](tasks/E26-T2-revalidate-and-repair-existing-points.md) — P1/L; dependencies: E24-T1, E26-T1.
- [E26-T3: Show honest map precision and prove real pin behavior](tasks/E26-T3-show-honest-map-precision.md) — P1/M; dependencies: E26-T1, E14-T5.

## Risks and open questions

Street-level sources do not support rooftop claims. Neighborhoods and official districts differ, and source locality names can be inaccurate. A changed query key does not automatically invalidate existing selected points. Automatic repair must preserve owner-verified locations and consistent map/list/filter semantics.

The implementer must resolve concrete schema/contract and accepted numeric budgets in the promoted task/plan revisions. Irreducible ambiguity, access loss, protected-field conflict, and destructive recovery are exceptional manual cases; transient errors and routine backlog work must resume automatically. Existing ADR-015 backup deferral remains unchanged.

## Invalidation triggers

Material changes to source semantics, geospatial confidence/precision claims, automatic write authority, schema/contracts, provider choice or cost, release trust boundaries, or the evidence supporting this recommendation return the spike to review. Task sequencing, test, rollout, or rollback changes follow implementation-plan revision rules after approval.

## Exit checklist

- [x] Bounded question answered with one recommendation.
- [x] Evidence and uncertainty distinguishable in the linked audit.
- [x] Affected modules/domain documents and decisions identified.
- [x] Proposed task scope, acceptance, dependencies, and exception handling recorded.
- [x] Outputs are documentation only; no production or disposable proof artifacts created.
- [x] Owner direction to start E26 recorded as approval to advance revision 1 into task refinement and planning; implementation approval remains separate.

## Owner decision

See [owner decision](OWNER_DECISION.md). The owner selected E26 and directed “let's start”. This is recorded as approval to advance the existing spike recommendation into task refinement and planning. It does not approve the implementation plan prepared afterward.

## Municipal-first follow-up (revision 2)

The owner explicitly requested implementation, merge, deployment verification, and assessment of backfill after the municipal-first proposal. This supersedes the earlier hosted-provider-only scope for E26-T4; completed T1–T3 remain historical facts. See [the follow-up specification](MUNICIPAL_FIRST.md) and [owner direction](OWNER_DECISION.md).
