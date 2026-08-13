# Data Source Baseline

## Source inventory

The workspace is a greenfield data drop, not an existing application repository.

- `../../est-test/result.json`: approximately 21 MB Telegram Desktop JSON export and the canonical historical message index.
- `../../est-test/photos/`: 25,733 JPEG files, approximately 2.2 GB.
- `../../est-test/video_files/`: 75 unique MP4/MOV videos plus thumbnails, approximately 537 MB.
- `../../est-test.tar.gz`: approximately 2.85 GB archive duplicating the extracted export.
- Total workspace footprint is approximately 5.4 GB because both the extracted data and archive are present.

The raw export and archive are immutable inputs. They must be excluded from Git, Docker build contexts, test fixtures, and production application images.

## Channel metadata

The JSON identifies:

- Name: `El Estate | Покупка Варшава`.
- Export type: `public_channel`.
- Numeric ID: `2180077318`.
- Message date range: 2024-07-11 through 2026-08-12.
- Total records: 27,082, including 27,075 message records and 7 service records.

The export does not include a public channel username, but the owner supplied and the public Telegram preview verified `elestate_warszawa`. Historical source links can therefore use `https://t.me/elestate_warszawa/{message_id}` while retaining the numeric channel/message IDs as lineage.

## Message shape

All records include an ID, type, date, Unix timestamp, text representation, and text entities.

Common optional fields include:

- `photo`, `photo_file_size`, `width`, and `height`.
- `file`, `file_name`, `file_size`, `thumbnail`, `mime_type`, and duration.
- `reactions`.
- `inline_bot_buttons`.
- `reply_to_message_id`.

Text may be a string or a mixed Telegram export structure. Extraction must support both the `text` value and typed `text_entities`, preserving the original Unicode content.

The dataset has no native latitude, longitude, Telegram location object, stable album/group ID, formal development ID, or reliable availability field.

## Listing population

An exploratory scan suggests the export contains on the order of 3,000 candidate real-estate posts across development/investment and unit-level templates. That value is a planning estimate, not an audited baseline or acceptance count.

Simple reproducible sanity counters find:

- 1,093 messages containing the token `Локализация`.
- 1,135 messages containing `Покупка |` without `Локализация`.

Those token groups are not equivalent to development and unit offers: templates overlap, drift, and include non-candidate context. The versioned detector in [E2-T2](../epics/E2-historical-export-parser-audit/proposed-tasks/E2-T2-implement-candidate-detection-and-typed-extractors.md) must define exact reason codes; [E2-T5](../epics/E2-historical-export-parser-audit/proposed-tasks/E2-T5-audit-the-complete-export.md) then publishes the authoritative count and split for that parser version.

Common parseable fields include:

- Location or address.
- Warsaw district.
- Market type.
- Room count.
- Area or area range.
- Price or price range.
- Currency, usually PLN.
- Floor.
- Delivery quarter/year.
- Parking price.
- Development name.
- Contact mention or phone number.
- Google Maps URL.

The source mixes Russian, Ukrainian, and Polish; Cyrillic and Latin address forms; decimal commas; varied whitespace; and free-text prose.

## Coordinates and location quality

- The export contains no explicit coordinates.
- About 661 unique raw location strings collapse to roughly 628 normalized values.
- Nineteen messages contain Google Maps short links; these are high-value location hints but still require controlled resolution and validation.
- District-only locations can produce only approximate pins and must not be presented as exact building coordinates.
- Around 72 candidate posts may be outside Warsaw or omit an explicit Warsaw marker.

Every geocoded result needs:

- Original query.
- Normalized query.
- Provider.
- Provider result identifier when available.
- Coordinates.
- Precision/type, such as building, street, district, or city.
- Confidence.
- Raw provider response or a durable diagnostic subset.
- Review status and timestamp.

Coordinates outside a configured Warsaw bounding region must enter review rather than automatically appearing on the map.

## Media relationships

There are 26,991 message-level photo references and 25,733 files on disk. Repeated references mean reference count is not a unique-file count.

Most photo messages contain no text. The export omits Telegram album IDs, so gallery association is heuristic:

1. A text-bearing candidate listing starts a possible media group.
2. Adjacent media-only messages in the same chronological run may be attached when their timestamp gap stays within a configured window, initially 120 seconds.
3. A new text-bearing listing, service message, long gap, or explicit reply boundary ends the run.
4. Every association stores the rule and confidence that created it.
5. Source-message ownership is never overwritten, even when a media item is associated with an offer.

The 78 video message references resolve to approximately 75 unique video files, with source thumbnails. The importer must verify file existence, type, and safe relative paths before creating a public media record.

## Identity and lineage

Use `(source_channel_id, source_message_id)` as the immutable source identity.

Do not use these as the sole canonical offer identity because:

- A single offer may be reposted.
- A development can have many unit offers.
- A text post and adjacent gallery messages belong to one visible item.
- Future edited messages need revision history without creating duplicate current records.

Canonical entities and keys are defined in the [data model](../contracts/DATA_MODEL.md).

Every derived offer field must retain:

- Source message reference.
- Parser version.
- Extraction confidence.
- Whether it was parsed, normalized, geocoded, manually corrected, or inferred.
