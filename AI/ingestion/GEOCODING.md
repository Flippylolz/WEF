# Geocoding Options

## Workload

- Historical seed: roughly 628 normalized address/location strings, subject to parser audit.
- Live ingestion later: a small number of new/changed posts per day.
- Every successful response is persisted in `GeocodeResult`; the application never geocodes again on page views.
- Queries are restricted/bias-validated to Warsaw/Poland and rejected/reviewed when out of bounds or low precision.

This is a low-volume backend workload. A free hosted production allowance is operationally safer than running a search index on the current shared 8 GB NUC.

[ADR-021](../decisions/adr/ADR-021-use-cached-provider-neutral-geocoding.md) selects Geoapify for the historical import through the owner's merged [PR #59](https://github.com/Flippylolz/WEF/pull/59). [D-002](../decisions/deferred/D-002-recurring-geocoding-provider.md) is **resolved** by [E8-T4](../epics/E8-telegram-live-ingestion/tasks/E8-T4-revalidate-geocoder-for-recurring-ingestion.md): retain Geoapify for recurring/always-on use under the same provider-neutral cache.

## Recommended MVP: Geoapify free

Official [pricing](https://www.geoapify.com/pricing/), [Geocoding API storage guidance](https://www.geoapify.com/geocoding-api/), and [terms](https://www.geoapify.com/terms-and-conditions/) checked on 2026-08-13 and **revalidated on 2026-08-21**:

- 3,000 credits per day.
- One forward geocoding request generally costs one credit.
- Up to 5 requests/second on the free plan.
- No credit card required.
- Commercial use is allowed with required Geoapify attribution/link.
- Geocoding results may be stored, subject to retaining required source attribution.

Fit:

- The estimated complete historical address set fits within one daily quota.
- Live updates should consume very few credits because results are cached.
- The API key stays in the backend/importer secret, never the browser.

Controls:

- Cap seed concurrency below provider limits.
- Persist responses/cache before continuing.
- Record remaining/reset quota headers where provided.
- Stop/defer rather than fall through to repeated calls when quota is exhausted.
- Display required attribution in the product/legal attribution area.
- Keep the provider interface replaceable.

## Free hosted alternative: LocationIQ

Official [pricing](https://locationiq.com/pricing) and [caching policy](https://help.locationiq.com/support/solutions/articles/36000216111-can-i-save-addresses-from-api-output-) checked on 2026-08-13:

- 5,000 requests per day.
- Up to 2 requests/second and 60 requests/minute.
- Limited commercial use with a prominent LocationIQ attribution link.
- Response data may be stored indefinitely, but free-account request/response caching is limited to 48 hours.

LocationIQ remains an available adapter, but it is not a mandatory historical comparator. Its account/cache terms must be re-evaluated before any future activation.

## Public Nominatim

The OpenStreetMap Foundation public Nominatim instance is not a recurring production provider. Its [official usage policy](https://operations.osmfoundation.org/policies/nominatim/) was checked on 2026-08-13.

A smaller one-time seed batch **may be permissible** only if the policy permits the specific use and all of these additional conditions are met:

- Maximum 1 request/second and preferably slower.
- Single thread/machine.
- Valid identifying User-Agent/contact.
- Persistent cache.
- Required OpenStreetMap attribution.
- No autocomplete or regular batch job.

This remains an emergency seed option if no hosted key is ready, not the live-listener backend.

## Self-hosted Nominatim

Nominatim is the strongest self-hosted candidate:

- Uses PostgreSQL/PostGIS.
- Imports a regional/country OSM PBF.
- Supports replication updates from a regional Geofabrik update feed.
- Provides forward and reverse geocoding.

For this project it would require a separate PostgreSQL/PostGIS dataset from the WEF application database, import tuning, update jobs, backups, and monitoring.

The current NUC has ample disk but only approximately 7.3 GiB RAM and already hosts other workloads. Nominatim documentation's performance tuning examples assume substantially more memory for large imports. A Poland import might be possible slowly with careful limits/swap, but it must not be assumed safe on the shared production host.

Use self-hosted Nominatim only after:

- Benchmarking a Poland or smaller supported extract off-production.
- Recording peak RAM, swap, disk, import duration, steady query memory, and update duration.
- Giving the geocoder its own Compose project, network, database volume, and resource limits.
- Proving import/update work does not degrade existing services.

Preferred self-hosting location is a separate host. If placed on the NUC, it is a later optimization, not an MVP dependency.

## Photon and Pelias

### Photon

- Open-source forward/reverse geocoder with structured address queries.
- Uses an Elasticsearch/OpenSearch-style index and JVM.
- Operational examples use large Java heaps for performance.

Photon is useful for search-as-you-type, but the additional search engine and memory pressure are not justified for roughly 628 offline addresses.

### Pelias

- Multi-service Docker geocoder built around Elasticsearch and several importers.
- Documentation states at least 8 GB RAM and potentially tens of GB of imported source data.

Pelias would consume the NUC's entire nominal RAM budget before existing applications. It is rejected for the current host/MVP.

## Historical quality and review test

During E3-T5, before any historical result becomes a visible pin:

1. Build a redacted fixture of 30–50 manually verified Warsaw addresses:
   - Exact building/street.
   - District-only.
   - Polish diacritics.
   - Cyrillic street prefix/transliteration.
   - Misspellings and ambiguous streets.
   - Out-of-Warsaw negative cases.
2. Query Geoapify through the common interface and durable cache.
3. Reconcile precision, accepted/rejected/out-of-area/unresolved results, latency, current terms, and attribution in aggregate/redacted evidence.
4. Manually review uncertain results and retain selected-result/review lineage; private addresses and provider payloads remain outside Git and CI.

Provider choice must be configuration, not branching business logic.

## Manual operator decisions (E18)

The owner console's Locations page (`/admin/places`) applies single-location
review decisions through the same lineage contract as the automated pipeline:

- Every decision appends one `location_geocode_selections` row with
  `actor_type="operator"`, `actor_id=<owner account id>`,
  `review_policy_version=warsaw-review-v1`, and a monotonic
  `selection_version`, then updates the `locations` row in one transaction.
- **Manual point placement** accepts a location with coordinates the owner
  placed on a map after checking the retained offer text: `reason_code=manual_accept`
  with `geocode_result_id=null`, `precision=building`, `confidence=1.00`,
  `selected_geocode_result_id=null`, and `out_of_scope=false`. Coordinates are
  validated against the versioned Warsaw bounding box (`within_warsaw`) before
  the write, preserving `ck_locations_accepted_public_point`.
- **Candidate acceptance** promotes the latest selection's geocode result when it
  carries an in-scope, error-free point; the copied precision/confidence and
  result id mirror the batch-accept CLI.
- **Rejection** (`manual_reject`) and **unresolve** (`manual_unresolve`, only
  from `accepted`/`rejected` back to `needs_review`) keep any existing point on
  the row; public map eligibility remains governed by `review_status`.
- Console decisions interleave safely with the recurring geocoder and the
  batch-accept CLI because versions are allocated per location inside the
  decision transaction.
- **AI-assisted place correction** (`ai_assisted_correction`, E19-T1) applies
  owner-selected display-name/address/district values from a pending review.
  Address or district application returns the location to `needs_review` and
  does not invent or move coordinates; the existing point stays until E18's
  map picker or geocoding re-verifies it.

## Recommendation

Use Geoapify for the historical import under ADR-021 and for **recurring live ingestion** under D-002/E8-T4 (revalidated 2026-08-21). Keep Geoapify-only aggregate quality evidence and explicit manual review from E3-T5. Public Nominatim remains ineligible for recurring jobs; at most it may be a potential small one-time seed fallback if its policy permits the specific use and every condition is met. Defer self-hosting until usage or provider terms justify a separate benchmark/host. Operator command: `wef-revalidate-recurring-geocoder [--live-check]`.
