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

## AI enrichment and parser-gap accounting (planned E19)

An AI-filled field is not ground truth. Batch reports reconcile candidate offers
and field proposals into applied, no-evidence, conflict, invalid, stale,
below-quality-threshold, provider-failed, and untouched outcomes. Report metrics
include field name, parser/model/prompt/schema versions, token/latency totals, and
source revision/evidence-offset coverage without raw source text or contacts.

Every active AI-filled field is labelled `ai_assisted` in offer presentation and
has durable current origin plus append-only history. The parser-improvement backlog
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
