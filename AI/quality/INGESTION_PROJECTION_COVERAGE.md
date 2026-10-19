# Ingestion extraction and projection coverage

This cohort of the owner's repository-wide 100% coverage request adds 32 boundary
cases for source extraction and replay planning. Six implementations now cover
all 818 statements and 282 branch paths and have independent 100% combined
line/branch floors in the [coverage policy](../../.github/critical-coverage.json):

- `extraction.py`: typed fields, exact source spans, warnings and contact guards.
- `extraction_numbers.py`: bounded numbers/rooms, complete quotes and currencies.
- `extraction_inventory.py`: complete, positive inventory quotes.
- `parser_replay.py`: field ownership, compatible currencies and coupled changes.
- `persistence_projection.py`: contact-free storage and public source projections.
- `persistence.py`: locked, bounded batches and progress after acknowledgement.

## Behavior evidence

| Boundary | Assertions |
| --- | --- |
| Numeric evidence | Missing/oversized number lists and incomplete or third alternative quotes remain unknown; absent/zero/oversized room tags remain unknown |
| Currency and inventory | Euro/dollar symbols preserve denomination; unknown markers invent none; a syntactically valid inventory row cannot have a zero total |
| Typed fields | Unsupported property labels remain unknown; semi-detached labels retain their type; conflicting districts produce exact warning spans; add-on starting prices do not become complete quotes |
| Unknown measurements | A nonnumeric area remains unknown without pretending it is a contradictory numeric range |
| Source offsets | Trimming removes surrounding whitespace and pin delimiters while retaining exact Python offsets for the surviving value |
| Contact privacy | Handles, phones and long digit runs are detected; ordinary prices/areas are accepted; overlapping, nested, unsorted and adjacent contact spans merge into one masked range |
| Replay evidence | Unknown groups and absent scalar bounds invent no fields; missing currency or differently denominated add-ons block coupled money updates |
| Persistence progress | Optional callbacks observe each acknowledged batch before terminal success; runs without callbacks retain the same counts |
| Existing add-on values | A newly proposed inclusion flag cannot overwrite the meaning of an existing parking/storage price |

The tests extend [replay planning](../../apps/backend/tests/test_parser_replay.py)
and [persistence projections](../../apps/backend/tests/test_persistence_application.py)
and add [extraction boundaries](../../apps/backend/tests/test_extraction_boundaries.py).
They use synthetic descriptions and source spans. Primitive parsing and trimming
helpers are tested directly for their input/output contracts; no provider request,
source archive, production data, parser-version change or coverage exception is
introduced. Existing parser benchmarks and real PostGIS replay tests remain active.

Run `make coverage-backend` for the complete locked Python/PostGIS report and its
per-file floors. The combined run passes 1,603 backend tests at 92.29% coverage.
All 42 completed domain/public/ingestion implementation floors pass; 1,152 lines
and 558 branch paths remain uncovered elsewhere. Remaining ingestion orchestration, admin services, adapters,
commands and operational code stay in scope. All applicable global and badge
thresholds must reach 100% before the repository-wide goal is complete.
