# Data Quality and Readiness

## Known data-quality risks

### Template drift

Location, price, area, rooms, and market data occur in multiple formats. Parsing must be additive and fixture-driven; a new parser rule must not silently change old results without a versioned reprocessing report.

### Ambiguous and misspelled addresses

Mixed `ul.`/`ул.`, Cyrillic transliteration, missing city names, district-only values, and spelling variants can resolve to the wrong place. Provider success is not enough; Warsaw bounds and precision must be validated.

### Duplicate and changing offers

Similar address, price, and area values can represent reposts or genuinely different units. Deduplication should produce a confidence-based relationship, not destructive deletion.

### Availability

There is no authoritative active/sold/withdrawn field. Source age is visible to users; no active status is inferred.

### Personal data

Source text includes phone numbers, Telegram mentions, and agent identifiers. Raw text remains internal for traceability. Anonymous APIs receive server-side masked text/contacts; only an active logged-in user not awaiting forced password change may request a separate audited, rate-limited, no-store reveal as defined in [Authentication, administration, and contact reveal](../security/AUTH_ADMIN_CONTACTS.md).

### Media safety

Never trust source file names as public paths. Reject traversal, normalize storage keys, derive MIME type server-side where practical, and do not serve arbitrary files from the import directory.

## Import accounting requirements

Every full or sample import produces a machine-readable and human-readable report containing:

- Source checksum, file size, channel ID, date range, and importer/parser versions.
- Records scanned by Telegram type.
- Candidate posts detected by template/rule.
- Offers created, updated, linked as possible duplicates, or rejected.
- Locations normalized, geocoded, cached, failed, out of bounds, or requiring review.
- Media references found, associated, missing, duplicated, rejected, or copied.
- Unknown hashtags, unhandled templates, and representative redacted failure samples.
- Stage durations and terminal run status.

Counts at each stage must reconcile to input records; failures are categorized rather than silently skipped.

## AI enrichment and parser-gap accounting (E19-T3)

An AI-filled field is not ground truth. Batch reports reconcile candidate offers
and field proposals into applied, no-evidence, conflict, invalid, stale,
below-quality-threshold, provider-failed, and untouched outcomes. Report metrics
include field name, parser/model/prompt/schema versions, token/latency totals, and
source revision/evidence-offset coverage without raw source text or contacts.

Every active AI-filled field has durable current origin plus append-only history.
E19-T4 labels those fields `ai_assisted` in offer presentation. The parser-improvement backlog
is built from reviewed gap records: typed expected value, exact immutable-source
offsets, and the parser version that missed it. Maintainers must verify candidates
before adding synthetic/redacted fixtures or parser rules. A later replay records
matching values as parser-confirmed and divergent values as conflicts; aggregate AI
fill rate alone is never treated as parser accuracy.

## Retention and environments

- Keep raw historical input read-only with a checksum.
- Production stores canonical data, import lineage, and selected media; it does not need the tar archive.
- Development uses a small, redacted fixture committed to Git, not a random slice containing personal contact data.
- Test fixtures use synthetic addresses/messages unless a reviewed source sample is essential.
- PostgreSQL/media persistence is server-local only; backups are deferred under [ADR-015](../decisions/adr/ADR-015-defer-backups.md), so permanent loss remains possible.

## Data readiness gate

Before importing the complete dataset:

- A parser fixture set covers every known template family.
- A dry run produces reconciled counts without canonical database writes; it may persist only its isolated ingest-run metadata and report artifact.
- Geocoding cache and rate controls are enabled.
- Warsaw bounding validation and precision thresholds are tested.
- Media paths are verified and the destination has sufficient disk.
- The redaction/logging policy is tested against messages containing phone numbers and mentions.
- Optional Groq place-review settings are absent by default and are not part of
  this gate or `/health/ready`; missing `WEF_GROQ_API_KEY` must not block import
  or deploy.

## E25-T1 source-evidence regression baseline (2026-09-05)

The versioned `parser-quality-v1` benchmark contains 75 invented/source-equivalent
cases: 60 labeled listing positives and 15 negative media/service/non-offer cases,
across Polish, Russian, Ukrainian and English. Ten property/market cases cover
houses, semi-detached houses and primary/secondary markets. Both audit examples
preserve their reported monetary semantics without copying original listing text,
contacts, source identifiers or locations. One contradictory rooms label is
explicitly unresolved and excluded from exact-value scoring.

This is a regression corpus, not a representative production sample. No production
sampling, reclassification, provider activation or historical repair was performed
for T1. The audit's dated null/ledger counts remain workload observations, not
accuracy measurements. Future source-template/time/visibility/version sampling
must keep restricted payloads outside Git and publish only aggregate evidence.

At unchanged parser `e2-v13`, candidate precision is 56/56 (100%) and recall is
56/60 (93.33%). All 15 negative cases are excluded from expensive recovery.

| Field | Exact / source-evidenced | False positives / source-absent | Unresolved |
| --- | --- | --- | --- |
| `apartment_price` | 43 / 55 | 0 / 20 | 0 |
| `parking_price` | 1 / 2 | 0 / 73 | 0 |
| `storage_price` | 0 / 0 | 0 / 75 | 0 |
| `parking_included_in_price` | 0 / 1 | 0 / 74 | 0 |
| `storage_included_in_price` | 0 / 2 | 0 / 73 | 0 |
| `area_sqm` | 41 / 41 | 0 / 34 | 0 |
| `rooms` | 31 / 41 | 0 / 33 | 1 |
| `market_type` | 50 / 50 | 0 / 25 | 0 |
| `property_type` | 46 / 60 | 0 / 15 | 0 |

The JSON baseline also reports source-absent rates using all 75 cases as each
field's denominator. An absent field is manually labeled from the invented source;
the production classifier separately uses `unclassified` when it cannot establish
absence. Empty denominators produce null accuracy, not a perfect score.

Known extraction failures are pinned by case and field. T2 must improve the audit
regressions without adding a failure to previously correct labeled fields. A case
with five incorrect fields is not five missed listings. Candidate confusion counts
and field-level counts are reported separately; no overlapping totals are summed
into a repairable-listing claim.

Reproduce the aggregate report from `apps/backend` with
`uv run python -m tests.parser_benchmark`; the evaluator reads only the reviewed
fixture and prints counts/rates, never source text. Run
`uv run pytest tests/test_parse_quality.py tests/test_telegram_fixture_safety.py`
for benchmark structure, no-new-regression, recovery-negative and fixture privacy
checks. Database tests verify issue/evaluation identity and retained lifecycle.

## E25 automatic recovery validation

Finite calibration covers supported scalar money, currency, area, rooms, market
and floor statements with at least ten positive and ten negative cases per enabled
field, plus complete-listing creation cases. This does not estimate production model
accuracy. Exact source offsets alone are insufficient: semantic role, currency, unit,
current snapshot and protected ownership are independent application gates. Unknown
formats remain observation-only. Report the live eligible denominator, unresolved
reasons, actual spend availability and human interventions before claiming acceptance.
