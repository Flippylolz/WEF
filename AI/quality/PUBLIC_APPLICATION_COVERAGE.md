# Public application coverage

The owner's 2026-10-19 request for repository-wide 100% coverage includes all
application behavior. This cohort completes the 16 catalog, contacts, estates and
identity application implementations and enforces a separate 100% combined
line/branch floor for each in the
[critical coverage policy](../../.github/critical-coverage.json).
The full PostGIS report measures all 20 files in these application layers,
including four namespace/re-export modules: 1,217 statements and 128 branch paths
are all covered. No public application file has a missing line or branch path.

## Added behavior evidence

The new tests add 22 cases to the existing public application suites:

| Boundary | Assertions |
| --- | --- |
| Selected-location and viewport cursors | Valid base64/JSON still refuses unknown versions, unsupported match ranks and timestamps without a timezone |
| Map filters | A quick-filter identifier requires its resolved cutoff; rooms and districts independently reject oversized groups and accept their inclusive limits |
| Quick filters | Every advertised preset resolves to its expected UTC cutoff; unknown identifiers remain refused |
| Authentication timing | A dummy-hash provider failure still produces the same invalid-credentials error and creates no account or session |
| Session resolution | An unexpired, unrevoked session refuses missing, disabled and deleted accounts |
| Account mutations | Password changes and disabling refuse missing/deleted accounts without changing stored accounts or sessions; deletion refuses an unknown identifier |
| Owner bootstrap | A normalized username owned by a regular user cannot be overwritten by owner bootstrap |
| Command composition helpers | Account keys are distinct UUIDv4 values and timestamps are current, timezone-aware UTC values |

The tests extend [browsing](../../apps/backend/tests/test_browse_catalog.py),
[map queries](../../apps/backend/tests/test_map_query.py),
[quick filters](../../apps/backend/tests/test_quick_filters.py) and
[identity behavior](../../apps/backend/tests/test_identity_application.py).
They use invented identities, tokens and catalog data. Existing real PostGIS/API
tests continue to exercise public visibility, stored projections, contact privacy,
favorites, view history and account persistence.

## Source simplification and scope

Quick-filter resolution previously checked the identifier against a one-member
registry, then checked the same identifier again. Its final refusal was
unreachable. Resolution now handles the supported identifier once and rejects
everything else. The public preset and its rolling cutoff are unchanged; no
coverage exception or runtime file exclusion is added.

Run `make coverage-backend` for the complete database-backed measurement and all
independent floors. Namespace/re-export files are also measured, with floors on
the implementations that own behavior. The combined domain/public application
run passes 1,571 tests at 92.04% backend coverage, leaving 1,181 missing lines and
586 missing branch paths outside the completed layers. The remaining ingestion/admin
services, adapters, commands and operational code stay in scope. Once those gaps are closed,
all applicable global and badge thresholds must also be raised to 100%.
