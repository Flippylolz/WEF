# E28 production delivery and backfill

## Releases and canaries

- T1: PR #377, parser e2-v16, accepted on healthy production release ffb338b (run 34199617611). Two previously missed template families covered by regression tests.
- T2: PR #380, production release 60f458179e22b897201d39ab9af65723b765ba35 (run 34202658289). Guarded v4 observe/apply canaries repaired both reported Warsaw streets and preserved the building-level control. Public map API and real browser selection verified; the selected street gallery had 10 items.
- T3: PR #383, production release c6db10640d977884284bb88f0eb30eefc1df0e3d (run 34204058362). One current-revision replay created the previously absent house. Normal geocoding/publication retained its actual town, selected an accepted city-precision point and exposed the existing Approximate area label. Default browser viewport includes the house with correct price, area and rooms. Four v5 observe/apply canaries and explicit verify-canary passed. Media awaited T4 at this stage.
- T4: PR #384, production release 1252a497e9c4a5b8b9e34ad5e353de9a9ac0d593 (run 34205281124), migration 0027. The current house album was prioritized through ordinary bounded discovery primitives without changing the global cursor. Normal worker recovery produced 10 unique gallery assets; all 20 public thumbnail/content HTTP checks passed. Browser selection, gallery and full-size image rendering passed. The historical metadata scan subsequently reached message 29761. Existing completed work was retained; additional repairable historical images entered the ordinary recovery queue.
- T5: PR #385 deployed as b27df267a7184bf029cd87ead8969f584adbbc4b (run 34206723530). Full bounded parser backfill completed successfully.
- T2 avenue follow-up: PR #386 deployed as 4f43adfac521e8807369853b704cf51e641c08e0 (run 34210144129). Retaining a common avenue token for al./Aleja/Aleje fixed the last apartment's address mismatch. All five latest offers passed public map, price/area/rooms and precision checks, with 48 unique gallery assets and 96 successful thumbnail/content HTTP checks. Explicit v6 canary verification passed. A fresh production browser showed all five in results; the recovered apartment opened with separate parking price and ten gallery images.
- T3 district-area follow-up: PR #387 deployed as 5a67fe4010978f4a5cf910ca5ecdb35f642f1789 (run 34212810239). Nine guarded v7 canaries completed application and explicit verification. All four district-only locations appeared in the public map with Approximate area labels. A fresh browser selected the Bemowo offer and displayed the area label, correct fields and ten-photo gallery. The revised local and CI browser matrices passed.
- T2 municipal identity follow-up: PR #388 deployed as c4d34c58e555adcd5c7e8ca9a3feb60dfdcda5ac (run 34215384687). All 16 guarded v8 canaries completed apply and explicit verification. All 32 seven-day offers passed actual public map/detail checks, including all 307 unique gallery assets and 614 successful image HTTP checks. Public precision distribution: 21 street, four building, four district, three city.

All canaries use existing source-current/owner-selection fences. No direct visibility/point overrides, provider budget increases or new dependencies were used. Receipts containing operational IDs remain outside Git; this record contains only aggregate acceptance and release references.

## Validation

The final integrated tree passed `make lint`, `make format-check`, `make typecheck`, `make contract-check`, and `make test`: 1,449 backend and 187 frontend tests, both coverage floors. Local frontend testing used two workers to avoid host CPU contention. Parent-squash rebases preserved the exact tested tree; current-head GitHub verification reran for each final branch. Five required contexts passed before each ordinary exact-head squash merge.

## Backfill

Frozen boundary: source message 29761. Active retained population: 28,312 messages. Dry-run and apply each completed 57 pages of at most 500 current retained revisions, with identical classifications: 24,954 non-candidates, 3,321 update candidates and 37 create candidates. Every apply page succeeded. Together with the separate latest-apartment and house canaries, 39 previously absent offers were recovered. The offer count increased from 3,338 after the house canary to 3,376 after the remaining replay. The five hidden offers and their identity fingerprint were unchanged. Live traversal remained aligned at 29761.

A seven-day comparison now has all 32 expected offer records and 307 current associated photos, with no missing galleries or pending media in that group. All 32 also passed actual public map/detail delivery verification after v8 revalidation. Five media quarantines compared against live Telegram had changed photo/album identities despite unchanged text and timestamps. A bounded metadata refresh used the existing live persistence path over 307 messages: 248 revised, 59 unchanged, zero created, checkpoint 29761. Current revisions completed ordinary media recovery; older quarantines were not force-reopened or treated as equivalent images. The five hidden-offer identities remained unchanged after this refresh.

## Initial passive acceptance (historical)

At the initial rollout, the 24-hour window was incomplete. E28-T5 and E28 remained in progress until real continuous delivery samples passed; no elapsed-time or replay substitute was accepted.

An hourly task heartbeat (`verify-e28-delivery-window`) checked the durable
production acceptance window, staying quiet unless a new actionable failure or
completion occurred. Its dedicated acceptance work ends with this checked closeout.

## Older recovered cohort follow-up

The 39 newly recovered offers all have complete current galleries. One older house
needed a bounded ten-message REPROCESS metadata refresh; all ten revisions were
updated, then the existing media worker completed its ten-photo gallery. This
operation used a separate run cursor and did not advance the live checkpoint.

Five older posts additionally exposed developer inventory price formats, a house
price-per-area annotation, and an exact district spelling. PR #389 deployed as 380d93203f0606e2c819d0dc9c35d990a8588a78
(run 34219222036), parser e2-v18 and normalization v9, and addresses these
parser/projection cases. Five exact-message dry-runs and applies each updated one
existing offer without creating duplicates. Two street abbreviations were individually compared with
official municipal identities and geometry, then accepted through the existing
operator selection service with current-source and protected-selection guards.
The recorded result retains building/street precision, municipal cache evidence
and explicit manual-accept lineage. No generic surname matcher or arbitrary point
was added. All eleven v9 canaries completed application and explicit verification. All 39
recovered offers then passed public map/detail checks with 315 unique gallery
assets and 630 successful thumbnail/content HTTP checks. All five corrected legacy
price/area/room ranges passed public field checks; both starting prices retain a
null ceiling. A real browser showed the development range and ≥ price, and opened
a recovered floor-plan image from its five-item gallery. The seven-day cohort
passed again: 32 mapped offers, 307 gallery assets, 614 successful image checks.
The five hidden-offer identities remained unchanged.

Final worker receipt: release `380d932`, live and remote head both 29761, healthy
progress and no active incidents. The durable acceptance state was still
`collecting`; no 24-hour completion is claimed.

## Live acceptance locality follow-up

The live monitor detected two newer offers with complete galleries but rejected
map locations. Exact source inspection showed that a Warsaw neighborhood and a
named Wilanów development were incorrectly classified as separate cities.
Normalization v10 recognizes Raków as Włochy and excludes the exact development
spellings Ostoja/Ostoya Wilanów from city inference. The existing street, building,
district, provider-city and protected-selection checks remain binding. This
repairs both fresh ingestion and retained normalized addresses through bounded
versioned revalidation. No raw offer descriptions are retained in this record.

The [municipal MSI registry](https://zdm.waw.pl/miejski-system-informacji/obszary-msi/dzielnica-wlochy/)
identifies Raków within Włochy; the [construction supplier's project record](https://www.soprema.pl/referencje/mapa-realizacji/osiedle-ostoja-wilanow)
identifies Ostoja Wilanów at Hlonda. The alternate spelling was reviewed in the
source with an explicit Wilanów district. Regression fixtures use an invented
street and retain rejection of other cities and unknown development-like names.

At this follow-up stage E28-T5 remained in progress pending the deployed
correction, guarded backfill and fresh continuous 24-hour delivery window.

The v10 release (#391, `4d4324f`, successful production run 34785859206)
completed the incremental parser backfill through message 29887: 126 current
messages, 13 update candidates, 113 non-candidates, zero creates; dry-run and apply
matched. Observation validated the development-label correction and accepted
controls while preserving the protected selection. The remaining numbered
address revealed two municipal address points on identically named streets in
different districts. Version v11 filters the complete bounded point set through
the already verified street and district geometry before testing uniqueness.
Two supported points still fail as ambiguous; provider ordering cannot choose a
winner. Real PostGIS tests cover separate districts, distance from the supported
street, both candidate orders and unresolved ambiguity.


## Completed live acceptance

On 2026-09-14T23:19:16.139429Z, the production worker reported acceptance `passed`
with 88,557 seconds of continuous durable samples beginning at
2026-09-13T22:43:18.871091Z. Release
`19557580e6989a09198af7ff2b49c2cc5b8e67aa` (#392; successful release run 34787043071)
was unchanged throughout that window. Samples were fresh, progress healthy,
all eligible backlogs empty, and there were no active incidents. The live and
remote checkpoints both remained 29887; this passive window does not claim new
channel traffic or substitute replay for live elapsed samples.

The final v11 canary completed seven accepted corrections and preserved one
protected selection. Explicit canary verification passed. All eight source
snapshots and the protected selection receipts were unchanged; the five hidden
offers retained the same identity fingerprint. Post-release replay over the
126-message increment through 29887 matched its dry-run: 113 non-candidates,
13 existing-offer updates, zero creates. Public browser checks verified both
recovered offers, their correct street/building precision and full-size galleries
of ten and eight images.

The rolling seven-day delivery cohort was 17/17 mapped after recovery and 13/13
at completion as four older posts aged out; no offer or gallery was missing.
The fixed 19-offer public verification set, including those older controls,
passed again at completion with all 306 thumbnail/content HTTP checks successful.
The rolling denominator decrease was not used to hide unresolved work.

The final implementation passed `make install`, `make lint`, `make format-check`,
`make typecheck`, `make contract-check`, and `make test` (1,464 backend and 187
frontend tests, with coverage gates). Every required PR check passed before
#391 and #392 merged, and both production releases passed their health gates.
E28-T5 and E28 are complete. The closeout includes cleanup of verified merged
E28 worktrees/branches and retirement of the dedicated acceptance heartbeat;
production ingestion and its durable health monitoring remain active.
