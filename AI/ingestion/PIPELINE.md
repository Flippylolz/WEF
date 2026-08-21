# Ingestion Pipeline

## Goals

- Import the Telegram Desktop export without loading the full JSON file into memory.
- Produce the same canonical result when a run is safely repeated.
- Preserve every source message even when candidate detection, parsing, media, or geocoding fails.
- Share all normalization and persistence logic with future live Telegram ingestion.
- Make heuristic decisions visible through confidence, reason codes, and reports.

## Pipeline boundary

Each source adapter emits a common `RawMessage`:

- Source platform and channel identity.
- External message ID and optional reply/group ID.
- Published and edited timestamps.
- Message/service type.
- Original text plus entity data.
- Source media descriptors.
- Raw payload and checksum.

The historical adapter reads Telegram Desktop JSON. The live adapter reads Telethon message/event objects. After conversion to `RawMessage`, both use the same stages.

## Pipeline stages

### 1. Source validation

- Open the source read-only.
- Calculate and record a SHA-256 checksum.
- Validate top-level channel metadata and message collection.
- Reject an accidental different channel unless the operator explicitly configures it.
- Record file size, channel ID, export date range, and importer release SHA.
- Begin an `IngestRun` before processing data.

### 2. Streaming raw-message import

- Use `ijson` to iterate `messages.item`.
- Flatten Telegram's mixed text representation while retaining the original structure.
- Upsert by `(source_channel_id, external_message_id)`.
- Compare payload checksums before updating an existing message.
- Preserve changed historical payloads as revisions.
- Count service, text, photo, video, empty, reply, and unhandled records.

This stage can commit in bounded batches. A failed batch rolls back without invalidating previously committed, checkpointed batches.

### 3. Candidate detection

Candidate detection is deliberately broader than field extraction. It assigns one or more reason codes, such as:

- Known purchase/market header.
- Location marker.
- Price marker.
- Area marker.
- Room hashtag.
- Google Maps link.
- Known development template.

A weighted threshold creates a candidate. Messages below the threshold remain stored and counted. New rules are versioned and tested against both positives and negatives.

### 4. Media grouping

Preferred evidence order:

1. Media on the same source message.
2. Explicit Telegram group/album ID when available from live ingestion.
3. Explicit reply relationship.
4. Historical-export adjacency and time-burst heuristic.

Initial historical time-burst rule:

- Begin at a text-bearing candidate.
- Walk forward through adjacent media-only messages.
- Associate while each gap is at most 120 seconds.
- Stop at a new text-bearing candidate, service message, reply boundary, or larger gap.
- Never associate media backward across another candidate.

Every relationship stores its rule and confidence. A fixture must cover adjacent listings posted close together so the heuristic does not merge both galleries.

### 5. Field extraction

Extractors are small deterministic rules with named versions. They return:

- Typed candidate value.
- Source span.
- Rule name/version.
- Confidence.
- Warnings.

Initial extractor families:

- Market and content type.
- Location/address and district.
- Development name.
- Apartment price/range and currency.
- Parking and storage price/range, plus explicit included-in-price statements.
- Area/range in square metres.
- Room count/range.
- Floor.
- Delivery quarter/year.
- Google Maps links.
- Telegram mentions and phone numbers for encrypted `ContactPoint` storage plus server-side public masking; plaintext remains restricted to the audited reveal path.

Parsing rules:

- Normalize Unicode and non-breaking spaces without altering stored source text.
- Accept decimal comma and decimal point.
- Remove grouping spaces only after identifying a numeric span.
- Do not convert unknown currency to PLN.
- Do not collapse a range to its midpoint.
- Do not infer missing zeroes or room counts from image captions.
- Treat conflicting high-confidence values as `needs_review`.

### 6. Normalization

Address normalization produces a comparison/search form, not replacement display copy:

- Trim and collapse whitespace.
- Normalize common street prefixes such as `ul.` and Cyrillic equivalents.
- Canonicalize `Warszawa`/`Варшава` to the city field.
- Canonicalize Warsaw district names while preserving diacritics in display values.
- Normalize punctuation and case for matching.
- Expand only a reviewed list of unambiguous abbreviations.
- Keep apartment/unit numbers separate from the map-location key where appropriate.

The normalizer version is part of the location cache key. Transliteration may add a geocoding query variant but must not overwrite the original address.

### 7. Location resolution and deduplication

Resolution order:

1. Previously accepted location for the same normalized address hash.
2. Verified coordinate extracted from a controlled Google Maps link resolver.
3. Cached geocoder result for the normalized query.
4. New geocoder request under provider policy.
5. `ungeocoded` review state.

Location grouping:

- Exact accepted normalized-address matches reuse a location.
- District-only results may group at district precision but are clearly marked and should be visually distinct or withheld if misleading.
- Fuzzy address matches create merge suggestions; they do not auto-merge by name similarity alone.
- Results outside the configured Warsaw bounds enter `needs_review`/`out_of_scope`.

Offer deduplication uses evidence rather than one unique key:

- Exact source identity always upserts the same source record.
- Exact normalized location, price/range, area/range, rooms, and near-identical normalized text can auto-link a clear repost at a high threshold.
- Partial matches create `possible_duplicate` relationships.
- A different unit number, area, price, or publication context creates a separate offer even at the same development.
- Dedup decisions and scores are included in the import report.

### 8. Geocoding

The geocoder is an interface returning a normalized result independent of provider response shape.

All calls require:

- Persistent query cache.
- Explicit connect/read timeouts.
- Provider-specific rate limiter.
- Bounded retries for transient failures only.
- Provider and policy-compliant identification/attribution.
- Warsaw bounds validation.
- Precision and confidence mapping.

For the seed import, the public Nominatim instance may be used only as a small, one-time, operator-controlled batch:

- One process and one request thread.
- Absolute maximum one request per second, preferably slower.
- Valid identifying User-Agent with contact information.
- Persistent caching of every result.
- No autocomplete, recurring batch, or repeated query.
- Clear OpenStreetMap attribution and license compliance.

The importer must be able to stop and resume without repeating cached requests. Recurring Telegram ingestion uses the [D-002 recurring Geoapify retention](../decisions/deferred/D-002-recurring-geocoding-provider.md) from [E8-T4](../epics/E8-telegram-live-ingestion/tasks/E8-T4-revalidate-geocoder-for-recurring-ingestion.md).

Short Google Maps links are resolved only through a controlled, rate-limited resolver that records redirect targets and validates hosts. Redirect content is data, never executed.

### 9. Media verification and storage

For each media descriptor:

- Resolve only beneath the configured source root.
- Reject absolute paths and traversal.
- Verify the file exists and is a regular file.
- Stream SHA-256 calculation.
- Detect/validate MIME type and metadata.
- Telegram `photo` and thumbnail descriptors may infer a supported image MIME candidate from their relative suffix only; signature and decoder validation must still confirm the bytes before storage.
- Enforce configurable file-size and supported-type limits.
- Copy atomically to a temporary destination and rename on completion.
- Process media with bounded four-way filesystem/decode concurrency while retaining per-item transactions and batch checkpoints.
- Derive an opaque, checksum-based storage key.
- Create source ownership and offer-association records separately.

Physical checksum deduplication is allowed. Deleting one source relationship must not remove bytes still referenced by another asset.

Image derivatives:

- Preserve the original.
- Create at least one web thumbnail in a modern browser-compatible format plus a safe fallback if needed.
- Strip unnecessary metadata, including location metadata, from public derivatives.
- Record transformation version so derivatives can be regenerated.

### 10. Transactional persistence

For each canonical unit of work:

- Upsert source message/revision.
- Resolve or create location/development/offer.
- Store field provenance.
- Relate source and media.
- Update checkpoint and counts.

The transaction commits before acknowledging a live message/checkpoint. A replay after a crash sees the source uniqueness constraint and converges on the same state.

### 11. Reporting

Every run closes with the reconciled report specified in [Data quality and readiness](../data/QUALITY_AND_READINESS.md). A failed run still writes partial counts, last checkpoint, and a redacted error summary.

Dry-run mode performs source validation, detection, parsing, grouping, and geocoding-cache lookup without mutating canonical tables or copying media. It writes only its isolated ingest-run metadata and report artifact.

## Parser test corpus

Commit only reviewed synthetic/redacted fixtures:

- Development template variants.
- Unit template variants.
- Decimal comma and ranged values.
- Polish/Russian district and street forms.
- Price without currency and non-PLN currency.
- Missing/ambiguous location.
- Photo-only runs and two close consecutive listings.
- Video and thumbnail descriptors.
- Repost, edit, delete, and conflicting values.
- Malicious path strings and oversized/unsupported media.

Golden outputs include source identity, parsed typed values, confidence/reasons, normalized location, and media associations.

## Historical import runbook

1. Verify free disk space for database, selected media, and temporary derivatives.
2. Record the raw export checksum and make the source read-only.
3. Run source validation and parser dry run.
4. Review count reconciliation and unhandled-template samples.
5. Import raw messages and parsed records without geocoding network calls.
6. Run geocoding from cache, then the controlled seed provider for misses.
7. Review out-of-bounds, low-precision, and ambiguous results.
8. Copy/derive media after record identities are stable.
9. Run consistency checks and publish the final report.
10. Record reconciled counts, disk usage, and the accepted [ADR-015 no-backup risk](../decisions/adr/ADR-015-defer-backups.md) before enabling public traffic.

Never begin with a full media copy and external geocoding in the same unverified run.

## Future live Telegram adapter

### Authentication

- Use a dedicated Telegram account authorized to read the channel.
- Create API ID/hash through Telegram's official process.
- Bootstrap a Telethon session interactively in a controlled local/admin environment.
- Store the resulting session string as a production secret.
- Never print, commit, transmit in logs, or expose the session through API/debug endpoints.
- Restrict deployment access because the session can act as the authorized account.

### Backfill and listening

1. Resolve the configured channel entity and verify ID/title against production configuration.
2. Backfill from the last durable external message ID/date using Telethon message iteration.
3. Process oldest to newest through the common pipeline.
4. Subscribe to new-message events for the single configured channel.
5. Handle edit and delete events.
6. Persist a checkpoint only after the database transaction succeeds.
7. Periodically reconcile a small overlap window to recover missed events.

Delivery is at least once. Idempotent source keys make replay safe.

### Telegram-specific behavior

- Prefer live `grouped_id` for album association.
- Respect Telegram flood-wait responses exactly; do not blind-retry.
- Download media with bounded concurrency and resume/retry semantics.
- Record inaccessible/expired media without failing unrelated messages.
- Build a public link as `https://t.me/{verified_username}/{message_id}` only when the username/entity is verified.
- Private `t.me/c/...` links may require membership and are stored only when verified for the intended audience.
- On edit, store a revision and reprocess affected canonical records.
- On delete, mark the source deleted and recalculate offer visibility/history; do not erase audit lineage.

### Live-ingestion health

The worker records:

- Last event received and last event committed.
- Last successful Telegram connection.
- Current backfill/checkpoint.
- Recent flood waits and retry category counts.
- Pending low-confidence/review records.

A stale-worker alert is added with deployment monitoring. The public API remains read-only and operational during a Telegram outage, serving the last committed data.

## Manual review without an admin UI

The first release uses import reports and explicit maintenance commands:

- List unresolved/low-confidence records.
- Apply a reviewed location correction with operator identity and reason.
- Merge or unmerge locations/offers through a transactional command.
- Re-run derivation after a parser/normalizer version change.

Commands must write audit records. Direct ad hoc production SQL is an emergency operation, not the review workflow.

## Failure policy

- Permanent source/data errors: record and continue when isolation is safe.
- Transient database/storage errors: retry the bounded transaction, then fail the run if persistence is uncertain.
- Provider timeout/rate limit: defer the item and preserve a resumable checkpoint.
- Disk full or checksum mismatch: stop media processing immediately and mark the run failed.
- Unknown schema/channel mismatch: stop before canonical writes.
- Cancellation: finish or roll back the current transaction, persist checkpoint/report, and exit non-zero/cancelled.
