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

## Evidence so far

- E14-T5 merged in PR #362 and production release 34023893584 succeeded.
- `COMPOSE_PROJECT_NAME=wef-e26-t3 make test-backend`: 1,242 tests passed,
  91.06% coverage before the additional cursor regression.
- `uv run pytest tests/test_api.py -q`: 13 passed including no-bbox discovery,
  foreign/malformed cursor rejection and page-size bound.
- `pnpm --filter web test:coverage`: 185 tests passed; 95.99% lines,
  90.05% branches, existing thresholds retained.
- Strict backend mypy and frontend typecheck/lint passed during implementation.
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
