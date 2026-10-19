---
schema: ai-workflow/implementation-plan@1
epic: E28
title: Deliver current channel offers and galleries to the map
status: approved
revision: 7
owner: owner
spike_revision: 1
task_sequence:
  - id: E28-T1
    revision: 2
  - id: E28-T2
    revision: 3
  - id: E28-T3
    revision: 3
  - id: E28-T4
    revision: 2
  - id: E28-T5
    revision: 1
approval:
  required_role: owner
  status: approved
  decided_by: owner
  decided_at: "2026-09-08T07:09:17.634182+00:00"
  approved_revision: 7
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
2. **T2 — Warsaw street resolution:** depends on T1 (the initial epic baseline); a stack may proceed against PR #377 until it merges. `geocoding.py`, `address_evidence.py`, `geocode_candidates.py`, `municipal_geocoder.py` and versioned revalidation. Neighborhood identity and same-street geometry have separate negative evidence checks. Existing E26 source/owner/version fencing remains authoritative. Observe, canary the two audited locations, then apply bounded current-policy revalidation. No arbitrary point averaging or confidence-only selection.
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

## Revision 2 owner continuation

The owner requested implementation of the entire epic and a backfill afterwards. This authorizes continuing T2–T5 and production backfill after reviewed releases, not only starting T1. T2 explicitly depends on T1 so the epic baseline can use an ordered stack while CI runs. Backfill covers current retained offer revisions through bounded, resumable existing mutation paths, with changed/missed offers and galleries reconciled; existing protected selections and quotas remain binding. Do not wait for a second per-record or per-PR authorization. The 24-hour passive acceptance window may be scheduled after backfill with notification only for actionable results.

## Revision 4 integrated delivery stack

Under the owner’s full-epic authorization, T3 additionally depends on T2 because
both change address normalization. T3 stacks on #380, preserving its street fixes
while adding locality scope. T4 additionally depends on T3, which prepares the
rollback reader for additive migration 0027. Ordered PRs permit useful validation
while predecessors finish; no child completes before predecessor acceptance.
This includes revision 3’s gallery migration dependency and introduces no new
product/provider scope.


## Revision 5 delivery audit follow-up

The authorized full backfill exposed source-evidenced district-only Warsaw offers.
Under the owner's request that all new offer posts appear on the map, T3 now also
supports a verified municipal district area when the source has no street or house
number. Use one exact municipal district polygon and an interior representative
point, retain district precision and the existing Approximate area projection.
This stays within Warsaw and the existing provider, database columns and API
contract; it does not authorize guessed buildings, generic city pins, broad street
fallback, new dependencies, changed budgets or protected-selection overrides.
A district-only source must name one consistent canonical Warsaw district; city,
country, geometry, precision and source-current gates remain mandatory.

This is a bounded implementation adjustment within the full-delivery instruction,
not a claim that the owner separately supplied a street address. An optional
presentation preference was requested; absent a different preference, the existing
honest area label is used. The T3 follow-up stacks on T2's avenue-matching fix #386.
Production canaries and public map/browser acceptance precede completion.

## Revision 6: exact municipal names and streets across districts

The authorized backfill audit found municipal full names in `NAZWA_PODST` while `NAZWA_SKROC` stores initials. Match either exact official field on a single unique street identity; never fuzzy-match surnames. Validate all bounded official district polygons for a single street crossing districts when the source supplies none, and choose a street point within their union. Explicit source district and building-number constraints remain binding. Bump normalization and municipal cache targets, test wrong full names/independent identities/invalid boundaries and real PostGIS projection, then deploy and run guarded recent-offer canaries. This T2 follow-up starts after merged #387 and must preserve its area-only gates.

One official street geometry is valid but self-intersecting at junctions. Accept valid linework while retaining exact identity, finite geometry, source boundary clipping and an on-street representative point; simplicity is not a requirement for a road network. Invalid or zero-length geometries remain rejected.

## Revision 7: finish legacy backfill formats

The authorized complete backfill recovered 39 offers; five older sources additionally require Cyrillic per-area quote separation and complete developer inventory rows. Recognize an explicit developer header, aggregate only fully parsed bounded rows into advertised room/area/price ranges, and preserve starting-price lower bounds with the existing nullable maximum contract. Wrong currencies, malformed/partial rows, rent, add-ons and per-area-only prices remain guarded. Recognize the exact Praga Północ source spelling as the existing Warsaw district. Parser v18 and normalizer v9 enable guarded replay; verify invented regressions, real persistence and public lower-bound presentation. Reconcile the five sources and one changed older album through existing fenced services, preserve owner selections, and record any individually reviewed municipal address evidence.
