# E26-T4 deployment and production verification

## Implementation and release

- PR #369 (`0b9150c934a813966af5ce2a75fd48e9e15b09ea`) passed every required check in CI 34044289095 and merged as `18f08b57107d630e0937291d8fbd274286f62934`.
- Its initial release stopped before activation on a WebKit favorites test race. PR #370 waits for the real save response before reload; CI 34045389303 and release 34045825003 passed, deploying `14fbb3af9fc783428e5cb6c3b0038a933f5ee812`.
- The post-release negative probe found an empty municipal response with `crs: null`. PR #371 adds correct empty-result handling and malformed-CRS regressions. CI 34046588952 and release 34046973793 passed; active production SHA `fc3877dc7ea9cb2b141d48c4446ca0cb79ff3c3c` and public readiness were verified.

The final implementation passed `make verify`: 1,356 backend tests (91.22% combined coverage), 186 frontend tests, 186 repository-script tests, format/lint/types/contracts, delivery/rollback and shared-edge runtime proofs, production builds, architecture violations and Markdown links. The five-profile real-stack browser gate passed locally for the routing and browser changes and in required current-head CI/release verification. No tests were disabled and no retry count increased.

## Live municipal probes

At 17:05 UTC on 6 September 2026, the deployed adapter and production PostGIS passed six read-only probes using fresh city responses:

- The original `Gocław | ul. Ostrzycka` source and both Jugosłowiańska source forms reproduce the previously verified street points.
- The separate municipal Ostrzycka 2/4 address resolves at building precision; it is not substituted for either numberless listing.
- Ostrzycka in the wrong district and nonexistent house number 99 return no coordinate.

All three operator corrections retained their coordinates and selection versions. Their precision remains approximate street location; exact buildings for those listings remain unknown.

## Guarded canary

Nine observed locations were selected: four valid results (including three previously unmapped locations), two municipal ambiguities, and the three protected operator cases. Application completed four corrections and two unresolved outcomes; protected cases remained unchanged.

Read-only before/after checks verified all nine location/source identities, nine linked offers, and unchanged favorite counts. Every selected automatic result passed source-address agreement and matched its municipal cache coordinates. Both unresolved cases had no selected result or point. The three protected snapshots were identical before and after.

Anonymous production checks passed seven browser journeys for the four positive and three protected locations: map coordinates, precision labels, offer detail, rendering readiness and keyboard return focus. Both unresolved offers remained available through uncertain discovery and displayed `Location unresolved`.

Detailed bounded evidence is retained privately on the server at `/home/nuc/wef/state/e26-t4-verified-20260906.json`, mode 0600. It contains no raw source text, contact information or user identifiers. Source text used for agreement checks stayed inside the verification process; only aggregate relationship counts were exported.

## Backfill decision

A complete discovery pass covered 2,239 locations, 3,334 offers (3,320 visible), and three favorites. At the recorded checkpoint there were 206 further validated observations, four canary corrections, four unresolved observations/outcomes, 266 protected locations, and bounded pending/deferred work. The assessment demonstrates a useful backfill beyond the canary.

The owner subsequently explicitly requested the backfill against all offers. All nine canary snapshots were rechecked unchanged before expansion. The normal `verify-canary` command succeeded: `mode=apply`, `canary_verified=true`, and three audited operator actions. Catalog-wide application is enabled for the current v5 target.

At the first broader checkpoint, 283 locations were corrected and six remained unresolved; 266 protected locations were unchanged, 1,400 were pending, and 284 were deferred. All 2,239 locations and 3,334 linked offers remain covered by discovery. An earlier precision checkpoint already showed 181 previously unmapped locations gaining usable points, including four building matches; numberless street matches retain approximate street labels. Counts are moving checkpoints, not a claim that the queue has drained.

Public verification passed four newly backfilled locations through map coordinates, precision labels, offer details, map readiness and keyboard return focus, plus both unresolved discovery controls. All nine original canary snapshots remained identical after broader application, including the three protected Ostrzycka/Jugosłowiańska cases and their source/offer/favorite relationships.

Sequential bounded cycles use the existing shared provider ledgers and lease protections. Provider budgets and retry eligibility are unchanged. The hosted daily budget is exhausted, but municipal matches continue independently; hosted quota deferrals resume no earlier than the next UTC day. The recurring worker remains responsible for pending/deferred work and future new or changed locations. Implementation and verified rollout are complete; full-catalog processing continues automatically.

The catalog-wide authorization, aggregate checkpoint and public verification are retained at `/home/nuc/wef/state/e26-t4-all-offers-verified-20260906.json`, mode 0600, without raw source text or user identifiers.

A subsequent read-only repeatable snapshot rechecked all 377 corrected locations then present: source agreement, accepted status, selected coordinates and recorded precision all passed. The documentation follow-up passed `make verify` and Markdown-link validation.
