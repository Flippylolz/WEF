# E26-T3 verification

## Public behavior

Map and viewport listing queries include only accepted building/street locations
with a stored point. District/city centroids and unresolved locations never become
GeoJSON points. Backend `location_accuracy` projects effective precision, persisted
review status, uncertainty reason and label into map, list, selected-location and
offer-detail contracts. `accepted` describes stored review state, not a claim of
fresh verification. T1 owns source agreement on new decisions; T2 owns revalidation
of legacy decisions. Provider confidence is not a probability of positional accuracy.

`GET /api/v1/listings/uncertain` paginates visible, in-scope offers excluded from
map eligibility. It applies the existing non-spatial filters (including trusted
canonical district), explicitly ignores viewport membership, and returns no
geometry. Its `matching_count` is separate from `mapped_matching_count`; the latter
uses the supplied viewport and identical filters. Its `u1.` cursor cannot be used
as viewport pagination. Counts describe their separate query scopes and must not
be described as a combined viewport total. Hidden/out-of-scope offers stay hidden.

The uncertain section opens offer detail directly without moving the map. Existing
location/offer IDs and favorites survive quarantine. Selecting such a favorite can
load its visible offers and accuracy label without manufacturing a point. Street
points have a distinct outline and explicitly say “Approximate street location”.
Location confidence warnings are independent of offer data completeness. Unknown
or absent accuracy fields fall back to “Location unresolved”. No uncertainty
radius or area polygon is fabricated.

## Local verification

- E14-T5 merged in PR #362 and production release 34023893584 succeeded.
- `make verify` passed on code commit `4c034ec`: 1,243 backend tests,
  185 frontend tests, 91.10% backend coverage, all critical coverage floors, 186 script tests, contract
  generation/compatibility and negative gates, runtime/rollback proofs, production
  builds, architecture probes and Markdown links.
- `uv run pytest tests/test_api.py -q`: 13 passed including no-bbox discovery,
  foreign/malformed cursor rejection and page-size bound.
- `pnpm --filter web test:coverage`: 185 tests passed; 95.99% lines,
  90.05% branches, existing thresholds retained.
- Strict backend mypy (351 files) and frontend typecheck/lint passed. Production
  JavaScript is 567,632 gzip bytes across 17 chunks, below the unchanged 569,273 budget.
- Real PostGIS transition test preserves favorite access across quarantine,
  excludes coordinates from discovery, reconciles counts, tests pagination and
  district/price filters outside the viewport, then proves hidden offers vanish.

## Representative browser cases

The disposable browser seed adds invented offers at the audited representative
coordinates for Ostrzycka, January Jugosłowiańska and May Jugosłowiańska. The latter
is explicitly quarantined despite confidence 1.00. January is district-only.
Ostrzycka represents an accepted legacy street point with limited confidence;
it does not pretend T1 would newly accept confidence 0.50. A separate invented
nearby building supports cluster expansion. No private source text is seeded.

These tests prove rendering and discoverability policy, not live repairs.
Ostrzycka and Jugosłowiańska remain **not verified fixed in production** pending
T2 deployment, bounded canary receipts and current geometry/selection checks.

## Rollout and recovery

The optional fields preserve existing required geometry contracts. Deploy T3
before broad T2 application so quarantined visible offers remain discoverable.
T2 must not treat a passing synthetic browser case as permission to assert a live
case was repaired. Rollback must preserve coarse-pin exclusion and list-only
access; reverting to centroid point rendering is not a safe rollback.

The first browser pass exposed an assertion before map fitting settled; it now
waits for the actual viewport. The second pass passed 42 journeys and isolated a
mobile Chrome contact-button hover contrast failure. The hover green was darkened
while retaining white text. No test retries, contrast exemptions or budget changes
were introduced. These intermediate failures are not acceptance passes.

Final `make test-e2e` passed on `4c034ec` with 43 journeys across Chromium,
Firefox, WebKit, Pixel 7 and iPhone 13; 12 explicit non-Chromium WebGL skips,
zero retries and no failure artifacts. All three WebGL journeys pass in Chromium.
The runner seeded real PostGIS, migrated, built the API/web/edge and removed the
disposable project. No critical API routes were mocked. This closes synthetic
rendering/discovery acceptance, not production T2 repair acceptance.


CI run 34025491351 correctly blocked merge: Linux Firefox used the supported
no-WebGL fallback, so waiting for a map-fit URL change was an invalid assertion.
The discovery regression now accepts a completed map fit or the explicit fallback,
then still asserts stable viewport, precision, detail access and return focus.
The same journey additionally forces no WebGL on every profile; mandatory real
Chromium WebGL selection/cluster cases remain unchanged. A subsequent full local
run caught accessibility analysis before streamed metadata supplied the title;
the audit now requires a nonempty title before running every existing Axe rule.
No retry, timeout, accessibility rule or required browser was removed.

Final expanded `make test-e2e` passed: 48 journeys, 12 explicit non-Chromium
WebGL skips, zero retries and no failure artifacts. The production code is unchanged
from the complete `make verify` pass. `make lint test` also passed again (1,243
backend and 185 frontend tests), followed by frontend typecheck and the expanded
browser matrix. The two assertions only wait for actual application readiness.
