# E2 complete-export audit

## Merged e2-v2 source and versions

The read-only audit accepted the ignored Telegram Desktop export only after these
preconditions matched:

- File size: `21,634,277` bytes.
- SHA-256: `d349e27003058f470fa53e5cd9004fe6759e8db466bc690f132398e038816249`.
- Published range: `2024-07-11T13:02:34Z` through `2026-08-12T10:23:45Z`.
- Report version: `e2-report-v1`.
- Parser version: `e2-v2`.
- Media-grouping version: `e2-media-v1`.
- Terminal status: `succeeded`.

No raw text, contact value, payload sample, media path, generated detailed
report, or local source path is recorded here.

## Reconciliation

The final `e2-v2` run reconciled every stage:

- Source classifications: 26,991 photo, 78 video, 7 service, and 6 text
  records; total 27,082.
- Candidate detection: 2,991 candidates plus 24,091 non-candidates; total
  27,082 evaluated records.
- Media: 23,247 associated plus 3,900 unassociated descriptors; total 27,147
  descriptors.
- Association rules: 3,003 same-message, 20,222 time-burst, and 22 reply
  associations; total 23,247.
- Unassociated reasons: 3,326 no-active-candidate, 273 text-boundary, and 301
  time-gap dispositions; total 3,900.

The media total can exceed the record total because one source record may
contain more than one media descriptor. Source ownership remains unchanged by
association.

## Detector and extraction review

Candidate reasons overlap and therefore are not additive:

- purchase header 2,049
- unit marker 1,957
- room marker 2,567
- price marker 3,055
- area marker 1,241
- location marker 1,125
- development header 313
- Google Maps link 12

The parser assigned 2,659 unit and 125 development content types. It left 207
candidate content types unset: 188 have conflicting strong development/unit
evidence and 19 have no strong content-type evidence. This is intentional,
reviewable uncertainty rather than an inferred choice.

Material extracted-field counts are 2,881 apartment prices, 2,418 room ranges,
2,255 floors, 2,250 market types, 1,101 locations, 951 area ranges, 178 storage
prices, 108 parking prices, 94 districts, 32 delivery values, 17 development
names, and 12 Google Maps links. Contact-shaped spans are counted internally
for 4,982 candidates but no values are emitted in this audit.

Warnings remain explicit:

- 1,361 unknown-currency warnings: 1,300 apartment, 25 parking, and 36 storage
  values. Amounts remain typed while currency stays null.
- 188 conflicting-content-type warnings.
- 40 conflicting-value warnings: 32 floor, 5 storage-price, and 3
  apartment-price conflicts.
- 6 invalid-range warnings: 5 apartment-price and 1 room value.

## Boundary, template, and uncertainty review

The detector has no labeled ground-truth corpus for the complete private
export, so this audit proves deterministic accounting, not perfect semantic
classification.

- 2,174 candidates have a strong purchase or development header; 817 are
  admitted by a threshold-satisfying combination of weaker typed markers.
- The 181 candidates exactly at score 5 comprise 153 price-plus-unit, 17
  area-plus-price-plus-room, 7 area-plus-unit, 2 development-header-only, and
  2 location-plus-price-plus-room cases. These are the highest false-positive
  review priority.
- The 49 non-candidates exactly below threshold at score 4 comprise 47
  room-plus-unit and 2 area-plus-price cases. These are the highest
  false-negative review priority and remain excluded because a second
  independent high-intent signal is absent.
- The remaining non-candidates comprise 23,886 score-0 records and 156
  score-1-to-3 records. They are accounted for without inventing listing
  fields.
- The 188 conflicting strong templates remain null rather than being resolved
  from language, location, or ordering heuristics.
- All 3,900 unassociated media descriptors have a terminal reason. No-active
  candidate is expected for source galleries outside an active listing run;
  text boundaries and gaps are deliberate burst terminators.

The exploratory counters were not parser contracts. The rough estimate of
about 3,000 candidates differs from the audited 2,991 by 9 (`0.3%`). The
earlier 1,093 `Локализация` and 1,135 `Покупка |` counters used literal,
partially exclusive tokens; `e2-v2` scans multilingual reason patterns,
allows overlapping evidence, and separates candidate detection from nullable
content-type assignment.

## Material fixes and rerun result

The first complete run used `e2-v1` and reconciled all records but exposed two
material source-template gaps. `e2-v2`:

- treats later per-square-meter context as context, not the upper bound of an
  apartment-price range;
- recognizes source room hashtags with underscore separators, aggregates
  explicit room options into a typed range, and uses the same evidence in
  candidate scoring.

Sanitized regression cases cover scalar price plus per-area context, a true
price range plus per-area context, labeled room hashtags, and standalone room
hashtags. Relative to the first run, candidate count moved from 2,976 to
2,991, apartment-price extraction from 2,049 to 2,881, room extraction from
72 to 2,418, invalid-range warnings from 988 to 6, associated media from
23,123 to 23,247, and unassociated media from 4,024 to 3,900.

The complete export was rerun after the fixes. Two additional runs produced
identical reports after timing values were normalized, confirming deterministic
non-timing output.

## Post-merge correctness follow-up

An independent review completed after
[PR #42](https://github.com/Flippylolz/WEF/pull/42) merged and found bounded
parser correctness gaps. The corrective implementation is rule-bound as
`e2-v3` and the expanded aggregate report is `e2-report-v2`. It:

- accepts labeled rooms only as bounded integer scalars or ordered ranges,
  rejects malformed labels, and keeps invalid/conflicting room evidence in
  warning buckets;
- keeps explicit room hashtags as separate evidence, with a trailing word
  boundary that excludes prefixes such as `#2_roommate`;
- rejects unexplained extra price numbers while retaining the explicitly
  recognized per-area context;
- removes the runtime parser-version override, so reports and provenance cannot
  label the current executable rules as another parser version;
- emits a separate `e2-audit-evidence-v1` JSON artifact containing score
  combinations, threshold-boundary buckets, warning-code/field splits, the
  aggregate `e2-v1` comparison, and a SHA-256 digest of the normalized report.

The approved ignored export remained in the main worktree and was mounted
read-only into this isolated corrective worktree. Its recorded size and SHA-256
were verified before both runs. Two complete `e2-v3` runs succeeded and produced
the same normalized report hash:
`a9c2aef4f043f4e5708dc6e53a30d973439051bcf9d5cf61cc0bbfffe7b80a8c`.

The `e2-report-v2` counts reconcile:

- 27,082 records evaluated as 2,988 candidates and 24,094 non-candidates.
- 27,147 media descriptors split into 23,225 associated and 3,922
  unassociated.
- Candidate boundaries split into 2,659 above threshold, 329 exactly at
  threshold, 31 exactly one below, and 24,063 below the boundary bucket.

The exact score-5 combinations are 303 price-plus-unit, 16
area-plus-price-plus-room, 8 area-plus-unit, and 2 development-header-only
records. The exact score-4 combinations are 26 room-plus-unit, 3
area-plus-price, and 2 location-plus-price records. The safe audit artifact
retains the full aggregate score-combination map.

Warning splits remain aggregate and reviewable:

- conflicting content type 188;
- conflicting values: 32 floor, 5 storage-price, and 1 apartment-price;
- invalid ranges: 843 apartment-price, 592 rooms, 57 area, 7 storage-price,
  and 4 parking-price;
- unknown currencies: 1,092 apartment-price, 35 storage-price, and 25
  parking-price.

Against the historical complete `e2-v1` baseline, `e2-v3` changes candidate
count from 2,976 to 2,988, apartment-price extraction from 2,049 to 2,044,
room extraction from 72 to 1,733, invalid-range warnings from 988 to 1,503,
associated media from 23,123 to 23,225, and unassociated media from 4,024 to
3,922. The stricter price and room rules deliberately trade silent/invented
values for explicit review warnings.

## Reproduction

Run only with the ignored source mounted read-only and the expected channel
identity supplied through local environment configuration. `WEF_SOURCE_DIR` is
the host directory bound read-only to `/source`; `WEF_SOURCE_PATH` is the
container path and should remain `/source`.

```sh
export WEF_SOURCE_DIR=/absolute/path/to/the/ignored/export-directory
export WEF_HISTORICAL_EXPORT_FILENAME=result.json
stat -f %z "$WEF_SOURCE_DIR/$WEF_HISTORICAL_EXPORT_FILENAME"
shasum -a 256 "$WEF_SOURCE_DIR/$WEF_HISTORICAL_EXPORT_FILENAME"
make importer-dry-run
```

Compose writes the detailed JSON/Markdown and safe audit JSON into its
`media_data` named volume at the container-only
`/app/media/reports/e2-dry-run*` paths. Do not set
`WEF_INGESTION_REPORT_PATH` to a host path. To copy only the safe aggregate
artifact, use the importer UID that owns the mode-`0600` report and let the host
shell create the ignored destination with the same restrictive mode:

```sh
mkdir -p reports/e2
(
  umask 077
  docker compose --file infra/compose.yaml --profile operator run \
    --rm --no-deps --user 10001:10001 --entrypoint cat importer \
    /app/media/reports/e2-dry-run.audit.json \
    > reports/e2/e2-dry-run.audit.json
)
test "$(stat -f %Lp reports/e2/e2-dry-run.audit.json)" = 600
```

To reproduce the deterministic normalized evidence, preserve the first safe
artifact outside Git, rerun the importer, copy the second artifact, and compare
the embedded normalized hashes:

```sh
cp reports/e2/e2-dry-run.audit.json reports/e2/e2-dry-run.first.audit.json
make importer-dry-run
# Repeat the safe-artifact copy command above.
test "$(jq -r .normalized_report_sha256 reports/e2/e2-dry-run.first.audit.json)" = \
  "$(jq -r .normalized_report_sha256 reports/e2/e2-dry-run.audit.json)"
```

Run the repository acceptance gates before accepting the audit:

```sh
make install
make format-check lint typecheck test contract-check compose-config production-proof
make build
```

Detailed reports, source samples, contacts, and media remain outside Git, CI,
and routine logs. Database persistence, geocoding, media copy, and production
promotion remain E3/E7 work.
