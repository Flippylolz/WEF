# E28 production delivery and backfill

## Releases and canaries

- T1: PR #377, parser e2-v16, accepted on healthy production release ffb338b (run 34199617611). Two previously missed template families covered by regression tests.
- T2: PR #380, production release 60f458179e22b897201d39ab9af65723b765ba35 (run 34202658289). Guarded v4 observe/apply canaries repaired both reported Warsaw streets and preserved the building-level control. Public map API and real browser selection verified; the selected street gallery had 10 items.
- T3: PR #383, production release c6db10640d977884284bb88f0eb30eefc1df0e3d (run 34204058362). One current-revision replay created the previously absent house. Normal geocoding/publication retained its actual town, selected an accepted city-precision point and exposed the existing Approximate area label. Default browser viewport includes the house with correct price, area and rooms. Four v5 observe/apply canaries and explicit verify-canary passed. Media awaited T4 at this stage.
- T4: PR #384, production release 1252a497e9c4a5b8b9e34ad5e353de9a9ac0d593 (run 34205281124), migration 0027. The current house album was prioritized through ordinary bounded discovery primitives without changing the global cursor. Normal worker recovery produced 10 unique gallery assets; all 20 public thumbnail/content HTTP checks passed. Browser selection, gallery and full-size image rendering passed. The historical metadata scan subsequently reached message 29761. Existing completed work was retained; additional repairable historical images entered the ordinary recovery queue.
- T5: PR #385 deployed as b27df267a7184bf029cd87ead8969f584adbbc4b (run 34206723530). Full bounded parser backfill completed successfully.
- T2 avenue follow-up: PR #386 deployed as 4f43adfac521e8807369853b704cf51e641c08e0 (run 34210144129). Retaining a common avenue token for al./Aleja/Aleje fixed the last apartment's address mismatch. All five latest offers passed public map, price/area/rooms and precision checks, with 48 unique gallery assets and 96 successful thumbnail/content HTTP checks. Explicit v6 canary verification passed. A fresh production browser showed all five in results; the recovered apartment opened with separate parking price and ten gallery images.
- T3 district-area follow-up: PR #387 deployed as 5a67fe4010978f4a5cf910ca5ecdb35f642f1789 (run 34212810239). Nine guarded v7 canaries completed application and explicit verification. All four district-only locations appeared in the public map with Approximate area labels. A fresh browser selected the Bemowo offer and displayed the area label, correct fields and ten-photo gallery. The revised local and CI browser matrices passed.
- T2 municipal identity follow-up: PR #388 merged as c4d34c58e555adcd5c7e8ca9a3feb60dfdcda5ac. Exact full/short official names, bounded district unions for unique cross-district streets and valid street junctions resolve seven read-only probes. Production acceptance awaits the release and guarded v8 revalidation.

All canaries use existing source-current/owner-selection fences. No direct visibility/point overrides, provider budget increases or new dependencies were used. Receipts containing operational IDs remain outside Git; this record contains only aggregate acceptance and release references.

## Validation

The final integrated tree passed `make lint`, `make format-check`, `make typecheck`, `make contract-check`, and `make test`: 1,406 backend and 186 frontend tests, both coverage floors. Local frontend testing used two workers to avoid host CPU contention. Parent-squash rebases preserved the exact tested tree; current-head GitHub verification reran for each final branch. Five required contexts passed before each ordinary exact-head squash merge.

## Backfill

Frozen boundary: source message 29761. Active retained population: 28,312 messages. Dry-run and apply each completed 57 pages of at most 500 current retained revisions, with identical classifications: 24,954 non-candidates, 3,321 update candidates and 37 create candidates. Every apply page succeeded. Together with the separate latest-apartment and house canaries, 39 previously absent offers were recovered. The offer count increased from 3,338 after the house canary to 3,376 after the remaining replay. The five hidden offers and their identity fingerprint were unchanged. Live traversal remained aligned at 29761.

A seven-day comparison now has all 32 expected offer records and 307 current associated photos, with no missing galleries or pending media in that group. Location completeness remains a separate acceptance gate. Five media quarantines compared against live Telegram had changed photo/album identities despite unchanged text and timestamps. A bounded metadata refresh used the existing live persistence path over 307 messages: 248 revised, 59 unchanged, zero created, checkpoint 29761. Current revisions completed ordinary media recovery; older quarantines were not force-reopened or treated as equivalent images. The five hidden-offer identities remained unchanged after this refresh.

## Passive acceptance

The 24-hour window is not yet complete. Keep E28-T5 and E28 in progress until real continuous delivery samples pass; no elapsed-time or replay substitute is accepted.

An hourly task heartbeat (`verify-e28-delivery-window`) checks the durable production
acceptance window and stays quiet unless a new actionable failure or completion
occurs. It will record successful acceptance and pause after closing the epic
through the normal checked PR workflow.
