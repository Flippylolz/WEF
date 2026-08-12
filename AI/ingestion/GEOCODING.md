# Geocoding Options

## Workload

- Historical seed: roughly 628 normalized address/location strings, subject to parser audit.
- Live ingestion later: a small number of new/changed posts per day.
- Every successful response is persisted in `GeocodeResult`; the application never geocodes again on page views.
- Queries are restricted/bias-validated to Warsaw/Poland and rejected/reviewed when out of bounds or low precision.

This is a low-volume backend workload. A free hosted production allowance is operationally safer than running a search index on the current shared 8 GB NUC.

Provider selection and recurring-use revalidation are governed by [D-002](../decisions/deferred/D-002-recurring-geocoding-provider.md) and [E8-T4](../epics/E8-telegram-live-ingestion/proposed-tasks/E8-T4-revalidate-geocoder-for-recurring-ingestion.md).

## Recommended MVP: Geoapify free

Current published free-plan terms checked on 2026-08-12:

- 3,000 credits per day.
- One forward geocoding request generally costs one credit.
- Up to 5 requests/second on the free plan.
- No credit card required.
- Commercial use is allowed with required Geoapify attribution/link.

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

Current published free-plan terms checked on 2026-08-12:

- 5,000 requests per day.
- Up to 2 requests/second and 60 requests/minute.
- Limited commercial use with a prominent LocationIQ attribution link.

LocationIQ is a viable fallback if its result quality for the Warsaw fixture set is equal or better. Compare both providers against a manually verified address sample before final selection.

## Testing-only hosted alternative: OpenCage

OpenCage currently offers a 2,500 requests/day free trial at 1 request/second, but its documentation says the free plan is for testing rather than ongoing production use. Do not choose it as the free production dependency.

## Public Nominatim

The OpenStreetMap Foundation public Nominatim instance is not a recurring production provider.

It may be used for a one-time seed batch only under its policy:

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

## Provider selection test

Before committing to Geoapify or LocationIQ:

1. Build a redacted fixture of 30–50 manually verified Warsaw addresses:
   - Exact building/street.
   - District-only.
   - Polish diacritics.
   - Cyrillic street prefix/transliteration.
   - Misspellings and ambiguous streets.
   - Out-of-Warsaw negative cases.
2. Query providers through the common interface.
3. Compare correct point, precision, district/city, false-positive rate, latency, and attribution/terms.
4. Select one primary provider and retain cached fixture responses for deterministic tests.

Provider choice must be configuration, not branching business logic.

## Recommendation

Use Geoapify free for the historical import and initial production ingestion, with LocationIQ as the evaluated fallback. Keep public Nominatim seed-only. Defer self-hosting until usage or provider terms justify a separate benchmark/host.
