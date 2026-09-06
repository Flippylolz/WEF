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

Wider application remains locked: mode is `apply` restricted to the nine canaries, with `canary_verified=false`. The external canary proof passed, but the `verify-canary` command also unlocks catalog-wide application. Automatic approval review rejected that scope because the owner's “maybe we’ll need a backfill” wording was tentative. Explicit owner approval has been requested; no workaround or broad mutation was executed.

Provider budgets and activation gates are unchanged. The hosted daily budget is exhausted, but municipal matches continue independently. Deferred hosted/AI work must retain its existing pacing; no completion claim is made for the full catalog.
