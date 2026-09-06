# E26 production rollout evidence — 6 September 2026

Implementation and the production canary are complete; the remaining catalog is
revalidating automatically. **The three reported locations have verified quarantine
outcomes, not verified replacement coordinates.** Their ambiguous pins are removed,
their offers remain discoverable, and no precise replacement was invented.

## Reported cases

| Case | Independent geometry evidence before application | Persisted and public outcome |
| --- | --- | --- |
| Ostrzycka | Existing point was 0.0158 m from the municipal street line; the provider returned several distinct positions for that street. | `needs_review / ambiguous_candidates`; selected result and coordinates cleared; list-only “Approximate area”. |
| January Jugosłowiańska | Existing coarse point was 383.6949 m from the municipal street line. An observed street-form candidate was 3.5427 m away, but the corrected full candidate set contains multiple positions. | `needs_review / ambiguous_candidates`; selected result and coordinates cleared; list-only “Approximate area”. |
| May Jugosłowiańska | Existing town-hall point was 3,107.7268 m from the municipal street line. An observed street-form candidate was 3.5427 m away, but two matching street positions remained. | `needs_review / ambiguous_candidates`; selected result and coordinates cleared; list-only “Location unresolved”. |

Street alignment does not identify a building or a unique position along a street.
The approved ambiguity rule rejects distinct candidate positions rather than choosing
by score. This applies even when several positions lie along the same named street.
There was no manual coordinate override, source rewrite, or geometry-based production
inference to bypass that rule. The municipal geometry was independent audit evidence.

## Releases and verification gates

- T1: [PR #355](https://github.com/Flippylolz/WEF/pull/355), merge
  `6722ecb79d47958a92eb3608aeade1a4a3cede9e`, successful release
  [34016504593](https://github.com/Flippylolz/WEF/actions/runs/34016504593).
- T3: [PR #363](https://github.com/Flippylolz/WEF/pull/363), merge
  `3fdcd7bb52b0e30d4160acaf8dab912ca51511c6`, successful release
  [34027321299](https://github.com/Flippylolz/WEF/actions/runs/34027321299).
- Rollback reader: [PR #364](https://github.com/Flippylolz/WEF/pull/364), carried
  by the browser audit correction in [PR #365](https://github.com/Flippylolz/WEF/pull/365).
  Release [34029703306](https://github.com/Flippylolz/WEF/actions/runs/34029703306)
  succeeded at `cea47610ea88da7408d5633bd3670503e847a052`, before T2 deployed.
- T2: [PR #357](https://github.com/Flippylolz/WEF/pull/357), green current-head CI
  [34029846674](https://github.com/Flippylolz/WEF/actions/runs/34029846674), merge
  `e73851915638e1fa6365016ae26ee254c148004c`, successful observation-only release
  [34030245708](https://github.com/Flippylolz/WEF/actions/runs/34030245708).
- Canary correction: [PR #366](https://github.com/Flippylolz/WEF/pull/366), green
  current-head CI [34031328811](https://github.com/Flippylolz/WEF/actions/runs/34031328811),
  merge `94a8932e00582e894a8ea9f52e2b0e86b5e4ceee`, successful release
  [34031682702](https://github.com/Flippylolz/WEF/actions/runs/34031682702).
  All WEF services were healthy on that SHA before application.

The five owner-approved E14 prerequisites merged separately in PRs #358–#362.
E14-T6–T9 were not implemented. Failing accessibility runs were diagnosed and
corrected; no failing, pending or skipped required check was accepted for merge.

`make verify` passed on the worker and normalization correction. Final code has
1,287 passing backend tests, 185 frontend tests and 186 script tests; format,
lint, strict types, contracts, critical coverage, negative probes, runtime/rollback,
build, architecture and links passed. Python 3.13.2 and Node 22.22.2 were used for
the correction. Real-stack CI retains all five browser profiles, zero whole-test
retries and the explicit non-Chromium WebGL exclusions. The combined local browser
matrix passed 48 journeys with 12 such skips; the release browser gates also passed.

The built prior reader passed readiness and a real PostGIS map query against the
actual additive `0026` schema. The new reader refused actual `0025` without validation
tables. See [rollback compatibility](ROLLBACK_COMPATIBILITY.md).

## Observation and canary

The private baseline contained 2,239 locations, 3,334 offers, three favorite pairs
and 263 protected selections. After observation began, every identity and protected
snapshot was unchanged. Initial public pagination traversed 566 uncertain offers
on 12 pages with non-spatial filtering and no geometry in any item.

The first ten-case observation exposed a provider translation defect: `South Praga`
was treated as an unrelated neighborhood instead of Praga-Południe. Application
stayed off and that generation was paused. The [narrow correction](PROVIDER_DISTRICT_NORMALIZATION.md)
recognizes reviewed provider translations and advances the request/cache generation
to `forward-geocode-v4`; it does not relax ambiguity, street/number, confidence,
city/country or protected-selection rules. Fresh v4 evidence then exposed the
multiple street positions described above.

One already-observed valid location was added to exercise acceptance as well as
quarantine, staying within the approved 25-case cap. The final eleven-case set
contained the three reported cases, three protected selections, automatic
building/street/district/city strata, and the positive validation case.

Applied outcomes were **one corrected/revalidated, seven unresolved, three protected**.
The seven unresolved outcomes comprised three candidate ambiguities, two address
mismatches and two low-precision results. Eight immutable application receipts
existed before expansion; no other location had been applied by this target.
Protected cases are intentional holds, not failed automatic repair or requests
for routine owner intervention.

## Persisted and live public checks

- All 2,239 baseline location IDs, 3,334 offer/location pairs, three favorite pairs
  and 263 protected selection snapshots were preserved after canary application
  and again after expansion began.
- Eligible decisions were recomputed from persisted v4 evidence and matched the
  stored review outcomes. The accepted case had positive source agreement.
- The three reported cases had null selected-result IDs and null coordinates;
  none appeared in map GeoJSON. Their existing offer IDs still opened details.
- At 12:14 UTC, all 570 uncertain offers across 12 pages omitted geometry and
  retained non-spatial discovery. The increase of four is a transition count,
  not an estimate formed by adding overlapping populations.
- Eleven anonymous production Chromium journeys passed at 12:15 UTC: three
  mapped and eight uncertain cases. Cards opened real detail dialogs with the
  backend accuracy label, closing restored keyboard focus, and uncertain selection
  left the viewport unchanged. No route mocks, authentication, writes, screenshots
  or raw production traces were used. A checker-only coordinate lookup error was
  corrected before the complete eleven-case pass; it was not counted as a pass.
- Subsequent automatic cycles left completed canary selection versions unchanged,
  establishing live replay/no-duplicate evidence in addition to database tests.

## Budget and ongoing automatic pass

The first observation snapshot used 792 of the existing 2,700 daily requests.
The v4 observation snapshot used 852; before expansion it used 902, leaving 1,798.
These are shared account totals including ordinary observation/foreground work,
not a claim that every intervening request belonged to the canary. No budget,
provider or cost authority was expanded.

Only after the persisted, geometry, identity and browser checks passed was
`verify-canary` recorded. Control is `apply`, with `canary_verified=true`, for
`warsaw-address-v3/forward-geocode-v4/warsaw-review-v2`. The old v3 generation stays
paused. Five bounded rollout controls were used across the two generations;
there was no per-location owner intervention or manual selection.

The first expansion snapshot already contained 58 terminal applications:
8 corrected/revalidated and 50 unresolved. It had discovered 1,301 locations,
with 138 protected holds, 1,098 pending and 7 cycle-budget deferrals. This is a
**dated progress snapshot**, not a completed-catalog claim. The durable worker
continues automatically in at-most-25-item cycles, scanning at most 100 locations
per cycle. Daily quota exhaustion defers safely to the next UTC budget day.
Unchanged terminal ambiguity remains settled; new source or policy evidence
creates fresh work. Protected decisions remain protected.

The rollout satisfies implementation/canary acceptance while the remaining
catalog pass continues asynchronously. Exact coordinates for the three reported
addresses remain unresolved. Do not describe quarantine as a verified coordinate
repair or claim that all existing locations have already completed revalidation.

## Independent geometry provenance

[Warsaw municipal WFS](https://wfs.um.warszawa.pl/serwis), layer
`ns92528565:ULICE`, EPSG:2178 (PL-2000), retrieved 6 September 2026:

- Ostrzycka: OBJECTID 4768 / ID 22776, Praga-Południe, fetched approximately
  06:48 UTC; GML SHA-256
  `73a2c03ff8eeab66791f26e1218730788a234274f23946c2caf2e233f35b56c4`.
- Jugosłowiańska: OBJECTID 607 / ID 21445, Praga-Południe; GML SHA-256
  `366afefe00ac1694e6dde72ea58e36446c94768b4ff56365a8b81c2189d11383`.

Distances used PostGIS `ST_Transform` into EPSG:2178 and `ST_Distance` to the
municipal line. Private identity snapshots, source/provider evidence and generated
reports remain outside Git; only redacted outcomes and provenance are committed.
