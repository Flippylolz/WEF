---
schema: ai-workflow/implementation-plan@1
epic: E28
title: Deliver current channel offers and galleries to the map
status: approved
revision: 1
owner: owner
spike_revision: 1
task_sequence:
  - id: E28-T1
    revision: 1
  - id: E28-T2
    revision: 1
  - id: E28-T3
    revision: 1
  - id: E28-T4
    revision: 1
  - id: E28-T5
    revision: 1
approval:
  required_role: owner
  status: approved
  decided_by: owner
  decided_at: "2026-09-08T06:48:39Z"
  approved_revision: 1
  evidence: OWNER_DIRECTION.md
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# Implementation plan

## Baseline and authorization

[Completed spike revision 1](SPIKE.md) establishes the production baseline. The owner explicitly requested the epic, completed spike, then starting fixes; [OWNER_DIRECTION.md](OWNER_DIRECTION.md) records the exact instruction and interpretation. Begin T1 after this plan. Future scope materially beyond these boundaries needs a revised plan; do not treat this as unlimited backlog authorization.

## Ordered changes

1. **T1 — current templates:** `extraction.py`, `parse_quality.py`, extraction regression tests and real persistence tests. Version parser/evidence identities so existing replay machinery can reevaluate. No database/API schema change. Negatives protect rent/services, per-area prices, addons and conflicts. Release normally; do not claim older stored offers are repaired until bounded replay is verified.
2. **T2 — Warsaw street resolution:** `geocoding.py`, `address_evidence.py`, `geocode_candidates.py`, `municipal_geocoder.py` and versioned revalidation. Neighborhood identity and same-street geometry have separate negative evidence checks. Existing E26 source/owner/version fencing remains authoritative. Observe, canary the two audited locations, then apply bounded current-policy revalidation. No arbitrary point averaging or confidence-only selection.
3. **T3 — nearby localities:** depends on T1. Extract and persist actual source locality, version scope/cache, resolve unique nearby municipality through existing provider, and render verified coarse precision. Touch location persistence, domain scope and public catalog/frontend only where needed; regenerate contracts if they change. Read compatible old rows; require a migration only if existing city/precision columns cannot represent the result. Test town-name ambiguity and viewport/filter discoverability; canary the audited house before broader rollout.
4. **T4 — recovered galleries:** depends on T1. Extend `media_recovery_discovery.py`/store and canonical-link integration to reopen only repairable unassociated work and rescan its bounded album context. Source revisions and verified media identity remain authoritative; use existing work/intention tables if sufficient. Test real transactions, idempotency, edits/deletes and adjacent albums. First dry-run/reconcile the cohort, then repair with existing worker/service paths and verify current unique gallery assets.
5. **T5 — delivery acceptance:** depends on T1–T4. Extend ingestion progress query/application/worker seams to observe actual offer-to-map/gallery outcomes. Use existing operator commands for bounded recovery with exact cohort counts; preserve dry-run/apply receipts. Test integrated public map/gallery behavior and real browser selection. Verify the five posts and a 24-hour live window. Keep task open when acceptance evidence is incomplete.

Each task has its own branch and PR against latest main or an approved immediate dependency stack. No production dependencies or provider budget increases are introduced. No other agents are delegated by this plan.

## Validation and privacy

Run all repository-required checks before each push and all five current-head required CI checks before squash merge. T1 has unit, benchmark, evidence-classification and PostGIS persistence regressions. T2–T4 require negative source/selection/association cases; T3 public changes require contract and browser checks. T5 establishes aggregate delivery metrics and real public acceptance. Fixtures are invented equivalents, not copied source descriptions. Never commit raw exports, images, source payloads, contacts, databases or sensitive reports.

## Risks, rollout and rollback

New parsing can create false positives or alter fingerprints; guard with benchmark negatives, exact evidence and idempotency tests. Location expansion can misplace same-name towns; require actual municipality/country and honest precision. Rescanning photos can cross an album; explicit identity and current-revision fences are mandatory. Terminal states can mask retryable misses; reevaluate only when an actual prerequisite/version changes to avoid hot loops. Existing provider outages/budgets retain deferred times. Immutable releases and per-stage pause controls provide code rollback; raw evidence remains retained, and persisted repairs require receipts rather than claiming data rollback. No global replay, direct force-visible SQL, global Docker cleanup or protected-value override.

## Completion boundary

This plan starts fixes with T1; the epic remains in progress until all task acceptance criteria and the complete production delivery window pass. Extending beyond nearby source-evidenced localities, changing AI auto-apply calibration, adding providers/dependencies or raising budgets invalidates this baseline.
