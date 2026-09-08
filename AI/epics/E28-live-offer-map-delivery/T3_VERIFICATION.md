# E28-T3 verification

Explicit locality and municipality are retained through extraction, query,
canonical location city and public display. Selection requires independently
matching municipality, city and country, confidence, unique position and scope.
The public map includes accepted city precision with its existing approximate-area
label, and the default viewport includes the audited northern locality.

88 focused tests passed, including negative municipality, country, ambiguous town,
confidence, precision and bounds cases. Full local `make test` passed 1,394 backend
and 186 frontend tests and coverage floors. A real PostGIS test replays the same
source twice, checks one canonical offer/location, performs normal geocode
selection and publication, and retrieves its truthful city point from the map.
`make lint`, `make format-check`, `make typecheck`, `make contract-check` passed.
Two-worker frontend execution isolates host CPU contention. Contracts are unchanged.

This release also prepares read compatibility for T4's additive 0027 per-source
media-discovery receipt so T4 can roll back to this reader. T4 must deploy after
this release. Production acceptance remains pending; source descriptions and
provider exports are not committed.


## District-only production audit follow-up

The seven-day delivery audit identified valid offers with only a Warsaw district.
The follow-up resolves one matching official municipal district polygon and uses
an interior point with district precision and the existing Approximate area label.
It cannot replace a supplied street/house or accept hosted coarse results, missing
city/country, contradictory district names, invalid geometry or wrong geography.
Reviewed Bielany neighborhood forms retain Warsaw/Bielany context.
Normalizer v7, review v4 and municipal cache prefix v3 make stale observations
eligible without changing provider allowances. No schema or API additions.
Focused, PostGIS, full-stack and deployed canary results are recorded below as
completed; the passive acceptance window remains separate.

The district follow-up passed 114 focused tests and full `make test`: 1,435
backend and 186 frontend tests, including coverage floors. Lint, formatting,
types and contracts passed. Existing public-query tests now explicitly cover
accepted district areas and still exclude unreviewed/hidden/out-of-scope rows.
Read-only production probes confirmed one valid municipal polygon and an interior
representative point for each of Bielany, Bemowo and Ursus. No source data was
changed by those probes. Browser and deployed acceptance remain pending.
