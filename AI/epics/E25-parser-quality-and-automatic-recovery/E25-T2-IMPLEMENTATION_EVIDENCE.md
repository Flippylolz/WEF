# E25-T2 implementation evidence

Parser `e2-v14` repairs the confirmed price, included-storage and room-tag gaps.
Explicit PLN/EUR alternatives select the supplied PLN quote without conversion;
actual same-currency ranges remain ranges. Per-area prices, add-ons, contradictory
inclusion statements and ambiguous currency combinations cannot replace apartment
price. Empty labels cannot consume the next line.

The 75 synthetic benchmark cases now have zero case/field failures (40 in the
recorded e2-v13 baseline), candidate precision 60/60 and recall 60/60. The benchmark
is a regression corpus, not an estimate of production accuracy. Real persistence
checks verify 78,000,000 and 139,900,000 apartment-price minor units, 3,900,000
parking-price minor units, 37.50 square metres, included storage and the public
price-filter projection. Negative tests exercise ambiguity and conflicting labels.

## Validation

- `UV_PYTHON=3.13.2 make install`: passed with locked dependencies.
- `make lint`: passed, including 17 architecture contracts.
- `make format-check`: passed.
- `make typecheck`: passed after adding explicit test type narrowing.
- `make contract-check`: passed; no API changes.
- `COMPOSE_PROJECT_NAME=wef-e25-validation make test`: 852 backend and 169 frontend tests passed. Backend coverage 90.44%; frontend branches 90.14%, lines 95.76%.
- `python3 scripts/check_markdown_links.py` and `git diff --check`: passed.

The full suite uses disposable PostGIS and exercises migration rollback/re-upgrade.
The same three existing backend warnings remain; no suppression was added.

## Delivery and recovery

No migration or production dependency is added by T2. Parser provenance advances
to e2-v14 for new extraction. No historical canonical writes, provider calls or
production changes were performed. A representative read-only historical diff
remains required before T4 activation. T4 is separately gated on E24-T1 and T3.
Runtime rollback can restore e2-v13 for new extraction; it does not reverse existing
data. This task remains in progress until dependencies, PR checks and an authorized
merge satisfy the definition of done.

## Changed files

- [Extraction rules](../../../apps/backend/src/wef_backend/features/ingestion/application/extraction.py)
- [Recovery extraction tests](../../../apps/backend/tests/test_parser_recovery_extraction.py)
- [Persistence and public-filter tests](../../../apps/backend/tests/test_parser_recovery_persistence.py)
- [Independent classification tests](../../../apps/backend/tests/test_parse_quality.py)
- [Evaluation lifecycle tests](../../../apps/backend/tests/test_parse_evaluation_integration.py)
- [T2 workflow record](tasks/E25-T2-repair-deterministic-extraction.md)
- [Epic progress](README.md)
- This evidence document.

## Production acceptance and completion

PR #330 merged as `d9f5e30` after all required current-head checks passed.
[Release 33973752178](https://github.com/Flippylolz/WEF/actions/runs/33973752178)
succeeded; API and worker were healthy on the exact SHA. Local release validation
passed 891 backend and 169 frontend tests with 90.52% backend coverage. The
75-case source-evidenced benchmark remained at zero field failures.

A read-only transaction compared e2-v14 with retained extraction for 100 current
linked sources: 92 changed, 8 unchanged; 55 had warnings. Changed field counts
(overlapping) were apartment price 25, area 60, market type 81, property type 48,
rooms 6, floor 4, district 16 and location 16. These are extraction differences,
not verified safe-write counts; T4 excludes location/district and guards warnings,
source identity and field ownership before any historical canonical application.

The metadata-only canary processed 100 sources in 10 batches, inserted 92 issue
rows and skipped 8 clean cases. Combined with ongoing live ingestion, transitions
retained 100 superseded evaluations and one resolved prior conflict. Duplicate
identities and invalid recovery eligibility were zero. No historical canonical
apply command or provider request was run by this acceptance probe.

All T2 acceptance criteria and the completed T1 dependency are satisfied.
