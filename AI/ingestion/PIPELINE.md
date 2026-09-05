# Ingestion Pipeline

## Goals

- Import the Telegram Desktop export without loading the full JSON file into memory.
- Produce the same canonical result when a run is safely repeated.
- Preserve every source message even when candidate detection, parsing, media, or geocoding fails.
- Share canonical persistence, revisions, visibility, and checkpoint behavior between historical and live Telegram ingestion.
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
- Tracked currency words (`злотых`, `złotych`, and close inflections) resolve to their
  ISO currency and may abut the amount (`850 000злотых` is 850 000 PLN, not 850);
  untracked currency words keep the amount reviewable with unknown currency.
- Remove grouping spaces only after identifying a numeric span.
- Do not convert unknown currency to PLN.
- Do not collapse a range to its midpoint.
- Do not infer missing zeroes or room counts from image captions.
- Treat conflicting high-confidence values as `needs_review`.

Location/address sources (in priority order):

1. Labeled lines (`Локализация:`/`Lokalizacja:`/`adres:` and equivalents) — high confidence. This
   matched the channel template through mid-2025.
2. Pin-line template fallback (`e2-v4`): when no labeled line exists, the address is read from the
   line starting with the 📍 pin emoji. The captured value stops at the next inline field emoji
   (for example a trailing `📐` area segment) and is accepted only when it carries Warsaw evidence:
   a street prefix token (`ul.`, `ул.`, `al.` and equivalents), a Warsaw city token, or one
   comma/pipe segment that exactly names a canonical Warsaw district (optionally behind a
   `район`/`dzielnica` word or a parenthesized neighborhood). Prose sections that reuse the pin
   emoji (`📍 Локация:` marketing blocks) and out-of-Warsaw localities fail closed to no location.
   The same accepted segment set populates the district field at medium confidence
   (`extract.location_pin` / `extract.district_pin` rules); divergent pin lines emit
   `conflicting_values` instead of choosing.

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

The importer must be able to stop and resume without repeating cached requests. Recurring Telegram ingestion uses the [D-002 recurring Geoapify retention](../decisions/deferred/D-002-recurring-geocoding-provider.md) from [E8-T4](../epics/E8-telegram-live-ingestion/tasks/E8-T4-revalidate-geocoder-for-recurring-ingestion.md). The live `telegram-worker` runs a supervised background loop that geocodes pending locations on the same schedule; operator `wef-import geocode` remains available for bulk catch-up. Address normalization cleans Telegram-shaped pipes, Cyrillic street prefixes, and area words before the provider call. Geoapify forward requests use a Warsaw rectangle filter plus proximity bias (`forward-geocode-v2`) so ambiguous Polish street names do not resolve to other cities. Locations left `ungeocoded` after a provider `no_result`, or `needs_review` after an `out_of_scope` selection, are retried when the negative cache expires or the normalizer/request version advances. For owner Groq place review on stubborn rows, see [Ungeocoded backlog and AI-assisted recovery](UNGEOCODED_BACKLOG_AND_AI_RECOVERY.md).

Sentinel policy: candidates whose address cannot be parsed share one durable `Unknown location`
row (`normalized_location_key(None)`). That sentinel is an accounting placeholder, not an address:
the geocode stage never queues it for provider resolution, because geocoding a non-address yields
a low-confidence Warsaw-centroid result that would pin every such offer to the city center. Such
offers stay `ungeocoded` and off the map until a source edit or a reprocess run supplies a real
address.

Short Google Maps links are resolved only through a controlled, rate-limited resolver that records redirect targets and validates hosts. Redirect content is data, never executed.

### 9. Raw event archive and background draining (E17-T1)

Every live Telegram event (new message, edit, per-deleted-id removal) is landed
verbatim in the `telegram_raw_events` table before any extraction or canonical
write. Landing is idempotent per (channel, message id, kind, payload checksum);
each row carries a durable processing ledger (`processed` / `failed` /
`skipped_non_candidate`, attempts, redacted error category). A supervised worker
task drains landed-but-unprocessed events every few seconds through the same
processor path, under the shared processing lock and the durable checkpoint, so
old replays cannot regress the cursor; failed events retry with a bounded cap
before counting as permanently failed. The archive is the replay source for the
parser re-import command and for future parser upgrades.

### 9. Parser replay over the raw archive (E17-T2)

The `wef-replay-parser` operator command re-derives canonical offers from the
archived raw events. Selection targets the latest archived event per message
whose primary offer stores an older `parser_version` than the running parser or
still points at the `Unknown location` sentinel. Each selected message is
re-persisted through the live upsert path under a `reprocess` ingest run with
the channel run lock, so revisions, visibility, and dedup fingerprints follow
exactly the organic-edit semantics. Completed replays select nothing again
(idempotent); messages that cannot be repaired are reported as
`stale_after_replay` instead of blocking the run. Replay volume against the
geocode stage remains bounded by the ADR-021 budget and pause machinery, and
the sentinel is never queued for provider geocoding.

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

### AI parser-gap feedback (E19-T3)

Owner-started AI offer autofill never mutates parser provenance in
`OfferSource.extraction_json`. Each applied or rejected candidate records a typed
field value, the parser version that missed it, and exact non-contact offsets into
the immutable source revision in separate E19 provenance tables.

Parser maintainers use a bounded owner-only report/export to review these gaps and
then add synthetic/redacted fixtures and deterministic rules through normal parser
tasks. Model output is not ground truth and never modifies executable rules,
versions, fixtures, or training data automatically.

During `wef-replay-parser`, a new deterministic value matching an active AI value
records `parser_confirmed` and transfers current field origin to the parser. A
different value records `parser_conflicting` and routes the offer to owner review;
replay does not silently choose or erase the AI history. A source edit marks the
old AI origin stale and clears the canonical field only when it still matches the
AI-applied value; a mismatch becomes an owner-review conflict. Stale AI values are
never served.

Historical non-offer messages ingested before the parse-issue ledger (E21-T1) can be
backfilled with `wef-backfill-parse-issues`. The command re-runs the current parser
on retained messages that have no `offer_sources` row and no existing ledger entry;
it is idempotent and safe to rerun after partial batches.

Parser `e2-v6` adds Elestate-format coverage: `Стоимость` price labels, `Продажа`
headers, and `#N_комнатная` / `N-комнатная` room tags. Parser `e2-v7` extends this
to Ukrainian Elestate posts: `Купівля`, `Ціна`/`вартість`, `N-кімнатна`, and
`ринок` market labels. Recover historical misses with `wef-replay-parser` after deploy.

### Parse-issue AI listing proposals (E21-T2)

Owner-only HTML at `/admin/ingestion-issues` lists deterministic parse misses from the
E21-T1 ledger. When AI curation is active and the message has no primary offer, the
owner can open **Review**, request **Generate AI listing proposal**, inspect
evidence-backed fields, and **Apply** one pending proposal to create an offer.

- Runs persist in `ingestion_ai_parse_runs` (migration `20260901_0018`) with a partial
  unique index on pending revision, 24-hour expiry, and the same fail-closed gates as
  place review and offer enrichment (enabled flag, ZDR, model allowlist, daily limit,
  masked source text).
- Applied offers use parser version `ai-parse-v1`; live ingest never calls Groq
  automatically.
- Denied paths (unknown revision, offer already exists, in-flight pending run, masking
  failure, daily limit, disabled curation) redirect back to review with a bounded reason.

Activation uses the same `WEF_AI_CURATION_ENABLED`, Groq secret, and ZDR settings
documented under owner enrichment controls below.

Operator batch catch-up (after UI smoke or when the ledger is large): use
**`wef-batch-ingestion-ai-parse`** from the **`api`** container. Full flags, JSON
output, compose examples, and the post-run geocode workflow are documented in
[OPERATOR_COMMANDS.md](../operations/OPERATOR_COMMANDS.md#wef-batch-ingestion-ai-parse).

```bash
# Link ledger rows that already have primary offers (no Groq), then generate/apply
# distinct parser_miss revisions with default 2.5 s spacing (~30 Groq RPM).
wef-batch-ingestion-ai-parse --link-existing-offers --limit 10
```

The command respects the application **20 generate runs per owner per UTC day**
(`ingestion_ai_parse_runs` only). Pace calls for Groq **~30 requests/minute**; do
not confuse the provider RPM limit with the WEF daily budget. Geocode and
map-ready promotion remain on `telegram-worker` — do not run parallel manual
geocode cycles while the worker is active.

Historical ledger backfill before batching: **`wef-backfill-parse-issues`** (see
[OPERATOR_COMMANDS.md](../operations/OPERATOR_COMMANDS.md#wef-backfill-parse-issues)).

### Owner enrichment controls (E19-T4)

Owner-only HTML at `/admin/offer-enrichment` wraps the E19-T3 interactors:

- **Preview** lists the immutable missing-field cohort, queue depth, and free-tier
  pacing estimate. **Start batch** is the only confirmation before eligible fields
  are written automatically.
- **Batch detail** shows processed/applied/skipped/failed counts, item outcomes,
  active AI origins, and POST/303 controls to process the next item, pause, resume,
  or revert still-matching applied values.
- **Parser-gap report** at `/admin/offer-enrichment/parser-gaps` groups redacted
  field events by offer, field, parser version, and model/prompt/schema versions.
  JSON/CSV export includes typed values and source offsets only—never raw source
  text, contacts, prompts, or provider bodies.

Activation requires `WEF_AI_CURATION_ENABLED=true`, a Groq API secret, verified Zero
Data Retention, and the exact approved model gate. When the flag or gate is
incomplete, the console shows a disable notice and public users continue to receive
`data_origin="parser"` unless an active AI origin already exists. Disabling the
feature stops new batches but does not delete append-only provenance rows; public
badges disappear when no active AI origin remains on displayed fields. Roll back
applied values through the batch revert control or by redeploying a prior image;
provenance tables are retained for audit either way.

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

## Live Telegram adapter

The Telethon adapter, bounded backfill, serialized new/edit/delete event processor,
fail-fast critical-loop supervision, checkpoint reconciliation, redacted status command,
and production worker service are implemented. Production gap and outage-recovery
evidence remain under E15-T3 and M4/B-003.

### Authentication

- Use a dedicated Telegram account authorized to read the channel.
- Create API ID/hash through Telegram's official process.
- Bootstrap a Telethon string session through the worker in a controlled local/admin environment using phone/login-code/2FA inputs when required.
- Load API credentials and an optional existing session from ignored local environment or deploy-managed production secrets; persist a newly generated session beneath the restricted Telegram session directory.
- Never print, commit, transmit in logs, or expose the session through API/debug endpoints.
- Restrict deployment access because the session can act as the authorized account.

### Backfill and listening

1. Resolve the configured channel entity and verify ID/title against production configuration.
2. On every process start, observe the remote head and poll forward from the durable
   polling boundary (zero until a range has been durably classified).
3. Process oldest to newest through the common pipeline.
4. Subscribe to new/edit/delete events for the single verified channel.
5. Handle edit and delete events.
6. Persist a checkpoint only after the database transaction succeeds.
7. Reconcile immediately and every 60 seconds: replay 20 recent message IDs, process
   ordered batches of at most 100, and cap each cycle at 500 source IDs, reserving
   up to 100 for older known-ID observations. A process restart after disconnect
   resumes durable polling, sweep continuation, and source backoff.
8. A supervised `recurring_geocode` loop resolves pending `ungeocoded` and retryable
   `needs_review`/`out_of_scope` locations every 60 seconds (configurable), up to 10
   per cycle, through the same Geoapify cache and durable budget machinery as
   historical import. Quota, rate, and transient provider errors defer to the next
   UTC day or 15 minutes without stopping ingestion; failed locations remain queued
   for the next cycle. After each non-empty cycle the worker also accepts in-scope
   pending geocode pins and promotes only offers whose locations are already
   accepted with coordinates (map-ready), leaving ungeocoded listings off the
   public catalog.

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
- Polling never infers deletion from an absent history item. Only a passive Telegram
  delete event can mark a source message deleted.

### Live-ingestion health

The worker records:

- Last event received and last event committed.
- Last successful Telegram connection.
- Current durable checkpoint, observed remote head, and last successful reconciliation.
- Recent flood waits and retry category counts.
- Pending low-confidence/review records.

`wef-telegram-worker-status` reports the durable checkpoint, observed remote head,
remote gap, last successful reconciliation, and critical-loop state. Compose liveness
requires a fresh transport heartbeat, running consumer, and a reconciliation completed
within three minutes. Worker freshness deliberately does not gate
`/api/v1/health/ready`; the public API remains operational during a Telegram outage and
serves the last committed data.

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

## Original archive recovery (E24-T1)

Archive replay consumes the original row UUID and stored payload/checksum; it no
longer reconstructs and re-lands a smaller live sibling. The historical decoder
preserves mixed text, entities, replies, and media descriptors. Legacy flattened
seeds require exact retained revision/checksum proof. New seeds retain verbatim
JSON. Channel/ID/evidence disagreement fails before canonical mutation.

A unique `telegram_archive_resolutions` receipt commits with the canonical
transaction. It records applied, already-canonical, non-candidate, superseded, or
deleted state and the source revision/tombstone proof. After commit, a conditional
acknowledgement marks the original archive row terminal. Restart after commit but
before acknowledgement projects the receipt without another offer/revision
mutation. A terminal row cannot accumulate attempts or reopen on a delayed error.
Cancellation propagates and pending work remains resumable.

Live/archive upserts and parser replay honor deletion evidence and source version
ordering. An archived delete can prevent creation even before a canonical source
exists. Older replay cannot replace newer content; unproved same-time differences
are conflicts. Known lossy projections may restore richer retained source evidence
only when exact lineage proves the repair and no newer source version intervened.

Automatic recovery uses a durable 100-original canary, 25-record batches spaced at
least five seconds apart, and a durable pause state. Canonical receipts verify the
canary before expansion. Read-only preflight and operator apply use the same ledger
and selection as the worker. Archive runs use reprocess mode and cannot publish a
synthetic live checkpoint. Attempted work and newly terminal work are separate;
failed/repeated work does not refresh successful progress.

Media descriptors remain evidence, not authorization to open archived paths.
Archive completion does not prove derivative completion. T2 owns the durable
cursor/retry changes; T3 owns independent media retry; T4 owns broader progress
health. These follow-ups are not complete merely because original-row recovery
is implemented.

## E24-T2 polling progress and fair retries

`telegram_channel_progress` separates canonical `applied_high_water_id` from
`polled_through_id`. Canonical transactions advance the former with `GREATEST`;
only durably classified polling batches advance the latter. Passive events and
late run completion cannot certify unseen history. Legacy source maxima populate
only applied progress, with polling starting at zero and coverage limited.
Operator status and runtime schema 1 expose both meanings through additive fields.

A cycle handles at most 500 source IDs, reserving up to 400 for forward polling
and 100 for explicit observations of older retained IDs. The sweep has a fixed
upper bound, persisted continuation, and a five-minute token lease. A resumed
worker rejects a stale observer's completion. Explicit empty Telegram messages
confirm deletion; omitted results and unavailable access remain unknown. These
metadata observations do not download media. Pending archive records and source
limitations keep canonical coverage visibly incomplete even at the remote head.

Raw retry eligibility is durable. Transport/provider/lock deferrals increment a
separate counter; five data failures quarantine the original with one exception
record. Delays start at five seconds, grow exponentially with positive jitter,
cap at 300 seconds, and respect any longer provider delay. Receipt-backed
acknowledgements bypass the data cap and delay. Relevant retry-policy changes
permit bounded re-evaluation, while unrelated releases leave the budget intact.
Legacy classification processes at most 25 rows per selection and preserves the
historical attempts count. Old lock exhaustion does not consume the data budget.


## E25-T1: Evidence-based parse evaluations

`source-evidence-v1` adds a classification independent of legacy `parser_miss` and
`parser_incomplete` outcomes. The detector recognizes supported labels and unit
terms separately from extraction, so a missing price or property type can be
noticed even when no warning exists. Exact source offsets are stored; source text
is not copied into evaluation metadata.

Outcomes are `complete`, `expected_non_offer`, `source_absent`, `extraction_miss`,
`incomplete`, `conflicting`, `provider_failure`, and `unclassified`. Provider
failure remains the separate existing AI run outcome until T3 connects scheduled
recovery; deterministic evaluation does not invent a provider failure. A missing
supported label is `unclassified` at field level, not proof of source absence.
Explicit absence expressions are source-absent. `complete` means no unresolved
recognized extraction gap; it does not assert every possible field was supplied.

Only evidenced listing gaps qualify for recovery. Conflicting warnings, media,
service content, unknown contexts and source-absent values do not. The manual
batch selector uses current revision identity, live deletion state and absence
of a primary offer; it no longer deduplicates by an arbitrary 200-character text
prefix or assumes all legacy parser misses are listings. This eligibility change
does not schedule or enable provider calls.

`parse_evaluations` is unique by source revision/parser/policy. The source row is
locked and its current revision rechecked before insertion. An unchanged source
is evaluated on a new version; repeated identities are a no-op. A newer evaluation
resolves prior classified field gaps only when all those fields are now complete;
otherwise it supersedes the previous observation. Source edits supersede old work.
`parse_evaluation_transitions` retains the prior observation and causing evaluation.
An older numbered parser generation is recorded as superseded without reactivating
recovery or closing newer evaluations. Unknown legacy parser families are not
numerically ordered against current families; T4 owns accepted-release scheduling.

Original legacy issue rows remain available. Legacy rows without an evaluation
of their revision/parser remain explicitly unclassified. Current classifications
are not silently retroactively attributed to an old extractor. Metadata backfill
is bounded and restartable, including clean and already-linked messages. T4 still
owns canonical historical convergence; successful classification alone does not
mean canonical values were repaired.

Migration `20260905_0022` adds evaluation and transition tables and advances runtime
readiness to that revision. Deploy schema before writers. Runtime rollback keeps
these additive tables and their history; explicitly downgrading the migration
removes only evaluation metadata and must not be confused with a data rollback.
The legacy issue outcomes remain readable by the old application.

## E25 revision 2 parser exception maintenance

Current source-evidence evaluations feed a unique revision/parser/policy/schema
recovery queue. Clean, irrelevant, source-absent, stale and deleted records cannot
become routine provider work. Manual and scheduled calls share durable reservations
and pacing; no ZDR path uses provider Batch/Files.

Automatic fills require calibrated literal role/unit/currency semantics, unique
non-contact evidence, a current offer/source snapshot and still-missing values.
Protected origins and inconsistent bounds remain unchanged. The observation canary
counts only fully validated cases; unsupported proposals do not qualify it. Complete
listing creation also requires deterministic property evidence and literal location
evidence, with atomic source-link and proposal completion.

This maintenance is distinct from T4 historical deterministic replay. Parser-version
convergence remains gated on the E24-T1/T2/T3 ancestor/completion contract. See the
[operator guide](../operations/OPERATOR_COMMANDS.md#e25-automatic-parser-exception-recovery)
for activation, pause, aggregate reporting and rollback.

## Accepted parser history convergence (E25-T4)

The optional worker compares current retained source revisions with the accepted
parser/policy/schema release identity. `parser_replay_releases`, `parser_replay_work`
and `parser_replay_field_events` retain canary state, fair claims and minimized
field lineage. The first 25 replayable records are read-only observations; a smaller
backlog uses all available replayable records. Observations are reused for guarded
application after canary promotion. Unchanged work identities cannot be reapplied.

Original JSON is decoded with the E24 decoder and checked against retained source
ID, text and checksum. Unsupported legacy/operator evidence, absent originals,
non-candidates, deleted sources and missing current offer links receive countable
outcomes. T4 does not fabricate archive events, reset E24 receipts or create offers;
unlinked eligible listing recovery remains T3's responsibility.

Application locks the current source, offer and field origins after parsing. A
field requires source offsets and either agreement with its retained parser value
or an empty canonical value. AI origins, conflicting origins and changed canonical
values remain protected; coupled price/currency groups stay together. Only allowed
scalar columns change. IDs, favorites, location/media/source relationships,
visibility and encrypted contacts survive. Source extraction, parser origin,
duplicate-suggestion fingerprint, evaluation lifecycle and durable progress commit
with each guarded write. Partial repairs retain old evidence for protected groups.

Migration 0023 extends origin metadata for parser-owned content/property fields;
it grants no additional AI field authority. Runtime rollback retains metadata.
Explicit per-job reversal checks current value/origin/source, restores only still
owned groups, pauses that release and records reverted/conflicting fields. Repeated
reversal is idempotent. No whole-table restoration or source checkpoint rewind occurs.
