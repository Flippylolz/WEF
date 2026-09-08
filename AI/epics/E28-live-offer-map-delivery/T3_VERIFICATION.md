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
