# Telegram, public catalog and parser audit — 15 September 2026

## Scope and conclusion

Owner-requested, unplanned operational audit of the verified channel
`2180077318` (`elestate_warszawa`), production release
`ecfc62832ac015d10dfa9ef0bb9224a2f0399691`, parser `e2-v18` and classification
policy `source-evidence-v3`. Freeze the comparison at source ID **29926**.
Observations are a dated snapshot, not a continuing completeness guarantee.

The public frontend exposes all **3,379 public-eligible canonical offers**:
**2,664 mapped** and **715 with uncertain locations**. This is not equivalent to
all source posts being complete, correctly parsed, or mapped. There are 19
retained text posts without primary offers that remain unclassified; manual
source-content review is outstanding. Four `extraction_miss` evaluations already
have linked offers and must not be reported as four missing offers.

## Reconciliation

| Population | Count | Interpretation |
| --- | ---: | --- |
| Retained active source messages | 28,477 | IDs 1–29926; no retained rows marked deleted |
| Text-bearing messages | 3,407 | Distinct current source messages |
| Text-bearing messages with a primary offer link | 3,388 | Source count, not distinct offer count |
| Text-bearing messages without a primary offer link | 19 | All classified unclassified; not proven offers or proven non-offers |
| Canonical offers | 3,393 | Includes explicitly non-public records |
| Public mapped offers | 2,664 | Accepted, in-scope locations |
| Public uncertain-location offers | 715 | Available in the separate non-spatial list |
| Hidden offers | 5 | Preserve owner visibility decisions |
| Needs-review offers | 9 | Seven out of scope, two unresolved in scope |
| Offers without gallery associations | 30 | 25 visible and five hidden; not a media failure diagnosis |

Public listing pagination is checked against the database public-eligibility
predicate, with UUID identity fingerprints rather than equal counts alone.
All 54 mapped pages and 15 uncertain pages returned 3,379 distinct offers, no
overlap, and the same SHA-256 identity fingerprint as the database query.
The browser default viewport includes all 2,664 mapped offers; a narrower
`20.7,52.0,21.4,52.4` viewport correctly returns 2,644. Expanding “Location
uncertain — outside map results” displays its 715 offers and the explanation
that map bounds do not constrain this list. A smaller viewport is not evidence
of lost ingestion.

Worker reconciliation, applied high-water, polling checkpoint and observed remote
head all equal 29926. The seven-day delivery cohort is 17/17 mapped with no missing
offers or galleries. `history_limited=true` remains meaningful: a caught-up worker
and a passing recent cohort do not establish historical source semantics.

The 1,449 integer IDs absent from retained source records were checked directly
against the verified Telegram channel in batches of at most 100. All returned
unavailable; **zero accessible missing source messages were found** through the
frozen head. This is an ID-coverage check under the current account permissions,
not proof that unavailable IDs never existed. A descending inventory attempt
was stopped after a four-second FloodWait; the subsequent gap check honored
Telegram retry delays and completed. Existing retained rows were not deleted or
rewritten based on unavailable responses.

## Backfill assessment

The deployed `offer_backfill_command` dry-run scanned all 28,477 active current
revisions in 57 pages, at most 500 per page, through the frozen head:

- 25,102 non-candidates.
- 3,375 existing-offer update candidates.
- Zero create candidates, stale outcomes or failed pages.

“Update candidate” means the parser produced a listing for an existing source;
it does **not** mean a field differs or will be repaired. The command's
`replay_current_revision` delegates application to the existing persistence path.
No blanket canonical apply is justified by these counts alone. Reclassification
is already current for every retained revision; another classification backfill
would add no coverage. No production data mutation was performed by this audit.

Historical location recovery is already in apply mode, with its v11 canary
verified: 1,454 corrected locations, 376 deferred for provider quota, 177 unresolved
and 268 protected. These are location populations, not offer counts. Preserve
retry schedules, provider budgets and protected selections; another manual sweep
must not be presented as a solution to quota exhaustion.

## Parser quality and historical provenance

Current, open evaluations reconcile exactly to 28,477 source revisions:

| Classification | Count | Recovery eligible |
| --- | ---: | --- |
| Expected non-offer | 25,070 | No |
| Complete | 1,747 | No |
| Conflicting | 1,254 | No |
| Incomplete | 124 | Yes |
| Extraction miss | 4 | Yes |
| Unclassified | 278 | No |

All 128 eligible evaluations have primary offer links. These measure field gaps,
not 128 absent listings. Of the 278 unclassified revisions, 259 are linked and
19 are unlinked. “Complete” is the policy outcome, not a human accuracy score.

The incomplete group includes 105 property-type gaps, 33 area gaps, two parking
price gaps and one apartment-price gap. Field counts overlap. Among conflicting
records, 1,042 flag apartment price, 173 rooms, 51 area and 32 storage price.
The classifier treats any extraction warning as an aggregate conflict; some
conflicting records also have independently repairable gaps. Source absence,
unsupported formats and real contradictions must be separated before repair.

Canonical offers have 1,325 null minimum prices, 375 null minimum areas, 473 null
minimum room counts, 604 unknown property types and 672 unknown market types.
These overlapping counts include non-public offers and are not accuracy or
safe-backfill counts: source evidence can legitimately be absent.

Current primary-source extraction provenance remains mixed: e2-v13 occurs in
1,619 source messages and e2-v14 in 1,639, while e2-v18 occurs in 18. Other parser,
legacy and manually produced rule versions remain. A source can contribute to
multiple version groups. Updating evaluation metadata does not update canonical
field values or provenance.

[PR #337](https://github.com/Flippylolz/WEF/pull/337) already owns E25-T4 historical
parser convergence. At inspection it remains draft with an explicit dependency
hold; its recorded compatibility baseline is older than e2-v18/v3. Refresh it
against current main and satisfy the existing T3 acceptance/dependency gates
before its guarded observe/apply rollout. Do not duplicate it or remove its hold
merely because historical CI was green.

## Media and archive findings

The worker reports 62,335 quarantined archive exceptions: 61,729
`ArchiveEvidenceError` and 606 `PersistenceBatchError`. These are event/revision
counts, not unique absent offers, and must not be subtracted from catalog totals.

Restricting media work to current active source revisions yields 3,476 quarantined
items across 3,464 revisions, with 3,250 distinct linked offer IDs. The reason is
`source_media_equivalence_unproven`. An offer can have completed photos and
quarantined work simultaneously; those 3,250 offers are not all empty galleries.
There are also 22,979 completed items and 1,864 unsupported unassociated items.

A targeted media refresh needs current remote photo/album identity evidence,
then ordinary discovery and derivative recovery. Reopening every quarantine or
reusing an old file reference without proving identity would be unsafe. Prior
E28 recovery established this distinction; the 25 visible offers without any
association are a useful first triage cohort, not proof all 25 should have photos.

## Proposed improvements — separate implementation PRs

1. **Historical parser convergence (existing #337):** refresh the version baseline,
   observe a bounded cohort, compare actual field/provenance differences, then
   guarded apply. Acceptance: stable IDs, favorites, visibility and protected
   origins; second unchanged run writes zero canonical changes.
2. **Parser field-level triage:** separate a genuine contradictory value from an
   unsupported format and from an unrelated warning. Prioritize apartment-price
   conflicts and property-type/area gaps. Extend synthetic regression fixtures
   across old/new templates, unit versus development ranges, starting prices,
   currencies and add-on prices. Measure per-field precision/recall and false
   positives; do not infer an accuracy percentage from policy classifications.
3. **Historical media recovery:** add a bounded, resumable metadata-refresh path
   for proven changed photo/album identities, with current-source fencing and
   unchanged live checkpoints. Start with source-verified empty galleries; test
   public thumbnails and full-size images after recovery.
4. **Whole-history delivery accounting:** retain a fixed historical cohort in
   addition to seven-day health. Reconcile source messages, unique offers,
   visibility, uncertain locations and galleries with exclusive reason counts;
   retain unresolved cases when they age out of the rolling cohort.
5. **Frontend discoverability:** show the mapped and uncertain counts together
   near the main total, with a direct action to the uncertain list. Existing
   uncertain offers are accessible but easy to miss behind the collapsed section.
6. **Unclassified-source review:** classify the 19 unlinked text posts through an
   authorized private review path before claiming every source offer is present.
   Promote only evidenced template gaps into synthetic tests and a separate fix.

These are proposals, not claims of implemented behavior or new approvals for
production dependencies, provider spending, protected-value overrides or source
publication. New implementation follows the repository's applicable workflow.

## Evidence and limits

Commands: `wef-telegram-worker-status`; read-only aggregate SQL transactions;
`python -m wef_backend.location_validation_command status`; the existing bounded
backfill function with `apply=False`; public API pagination and real-browser
inspection; GitHub CLI inspection of #337. Operational receipts stay outside Git.
No credentials, source bodies, contacts, media payloads or databases are committed.

Automatic approval review rejected extraction of source-text excerpts because
incomplete redaction could disclose private data to the local assistant session.
The audit uses aggregate evidence; the 19 unlinked posts remain manually
unverified. No claim is made that unavailable Telegram IDs prove deletion or
that retained historical content exactly matches every current remote revision.

Validation: locked dependencies installed with Python 3.13.2; `make lint`,
`make format-check`, `make typecheck` and `make contract-check` passed. `make test`
passed backend tests and coverage, then failed frontend timing/assertion checks
under default concurrency. The complete frontend rerun
`pnpm --filter web test:coverage --maxWorkers=2` passed all 187 tests, with 96.01%
line and 90.07% branch coverage. Markdown-link and whitespace checks passed.
No runtime source, contract, dependency or test behavior changed.
