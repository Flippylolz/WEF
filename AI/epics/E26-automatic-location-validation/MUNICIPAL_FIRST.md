# Municipal-first location resolution

The owner authorized this follow-up after three manual street-level corrections
were verified against Warsaw's municipal geometry. Their protected operator
selections remain authoritative. Buildings were not identified by those sources.

One coherent E26-T4 PR adds municipal lookup, then existing budgeted hosted
geocoding, then optional source-bound AI address recovery and one lookup retry.
AI cannot invent coordinates, a house number, a district, or a street absent
from the supplied address. Unresolved conflicts remain discoverable without pins.

Municipal data comes only from the city-published WFS endpoints:
https://mapa.um.warszawa.pl/ lists `wfs.um.warszawa.pl/serwis` and
`wms2.um.warszawa.pl/geoserver/wfs/wfs`. Read-only schema/sample probes on
2026-09-06 verified `ULICE` (name, district, EPSG:2178 lines) and
`wfs:punkty_adresowe` (street name, number, locality, stable ID, EPSG:2178 point).
Street-only sources use a point on the matched street line, never a building.
Numbered sources require an exact municipal address match. District/name
ambiguity and malformed/truncated responses fail closed. PostGIS handles the
projected geometry and coordinate transformation; no new production package.

Reuse the durable geocode cache and miss fences. Municipal cache keys rotate
weekly for refresh on use; no unbounded bulk WFS download. Bound response bytes,
features, timeouts and requests. Hosted fallback uses the existing Geoapify
account ceiling. AI uses the existing enabled, verified Groq runtime and shared
20-call daily ledger, only minimized address text, and durable per-source/version
results. Disabled or exhausted AI is an explicit outcome, never invented data.

The routing request version creates a fresh observation generation in the
existing E26 revalidation queue. No schema or public contract changes are needed.
Fresh ordinary locations use the new resolver. Existing locations are observed
first after release; verify bounded positive, negative and protected cases,
source/precision agreement, stable identities and live discovery before canary
application and any broad backfill. Record aggregates only. Never export user
identifiers, contact data or raw source messages for verification.

Tests cover source/municipal agreement, numbered and street-only precision,
duplicate/cross-district names, disconnected or invalid geometry, malformed XML,
network failures and bounded fallback, cache refresh, AI source grounding and
budget/disable behavior, and real PostGIS selections. Run `make verify`, the
real-stack browser gate and all current-head CI checks before ordinary release.
Rollout preserves all existing manual selections. Backfill is a separate guarded
operational action after production observation, not a blanket acceptance.


## Pre-release public-data proof

On 6 September, fresh exact-name WFS responses passed the adapter and local
PostGIS: Ostrzycka (21.079428886950907, 52.23405345808846) and Jugosłowiańska
(21.096650591179497, 52.2211301261555) reproduced the protected street corrections.
A separate municipal Ostrzycka 2/4 record resolved to a building point; it is
not substituted for either numberless listing. The actual city district uses a
single GML Surface/PolygonPatch, covered by a synthetic integration regression.
Exact equality avoids the server's incompatible advertised wildcard dialect.
Street and district response hashes, plus address response hash for buildings,
remain in cache evidence. Map attribution credits Urząd m.st. Warszawy.

Municipal requests have a per-client 100-request ceiling and one request/second;
foreground and repair each have bounded clients. Those public-service requests
consume no Geoapify credits. Existing hosted and AI ceilings remain shared.
The configured recurring worker still requires its existing Geoapify setup.

Hosted/AI quota exhaustion defers the affected work item until the next UTC day,
without pausing unrelated municipal lookups in the generation. Cycle limits
likewise defer individual hosted work while the bounded scan can try later
municipal matches. The durable shared provider ledgers still enforce all limits.


## Release harness follow-up

PR #369 merged as `18f08b57107d630e0937291d8fbd274286f62934` after all
required checks passed. Release 34044680044 stopped before activation because
WebKit's existing register/favorites journey failed. Its sanitized screenshot
shows the authenticated account with an unsaved favorite after reload. The test
clicked the star and immediately reloaded without awaiting the PUT response,
allowing navigation to abort the save. The bounded follow-up waits for the real
favorites endpoint to return 204 before testing persistence across reload. No
request mocks, added retries, disabled assertions or production behavior changes.
The municipal release remains unverified in production until a healthy release
and the guarded observation/application proof complete.


## First production observation

PR #370 passed CI 34045389303 and merged as
`14fbb3af9fc783428e5cb6c3b0038a933f5ee812`. Release 34045825003 succeeded;
the active SHA and public readiness were verified. The first 100-location v5
observation had 11 municipal matches (eight street, three building), two
explicit ambiguities, ten protected cases, and bounded pending/deferred work.
All three owner corrections retained their operator selections and coordinates.

A read-only negative municipal probe found that an empty address response carries
`crs: null`; the original adapter accessed that value before checking for empty
features. The follow-up treats a complete empty response as no match and requires
a valid EPSG:2178 CRS object for every nonempty response. Malformed nonempty CRS
shapes produce the existing transient municipal-unavailable outcome. Production
remains in observation mode until this regression and the canary proof pass.


The empty-response correction is released and the live municipal/canary checks passed. [Final verification and backfill state](T4_VERIFICATION.md) supersede the interim rollout notes above.
