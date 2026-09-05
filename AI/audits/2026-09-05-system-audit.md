# System audit and automation roadmap — 5 September 2026

The automated suites pass, but production evidence exposes a stuck archive replay loop, misleading accepted map points, and parser gaps that routine tests do not detect. Fix archive completion and address validation first; make replay, recovery, and releases automatic once their acceptance checks are reliable.

This is the review report requested by the owner, covering all six audit areas. It adds four researched epic workspaces and fourteen proposed tasks. Existing E14 remains the authoritative epic for general test confidence and code maintainability. No implementation approval is inferred from this audit.

## Scope and evidence

- Code baseline: current `origin/main`, `9fc612fc77dd752bc936bcc6cf8c6a13fe7d22b6`; verified by fetch on 2026-09-05.
- Existing suites ran against that checkout and its locked dependencies. Documentation lives on `doc/system-audit-epics-20260905` in an isolated worktree.
- Production observations: 2026-09-05, approximately 09:16–09:24 UTC. Public map/detail reads, redacted worker status, and bounded PostgreSQL transactions explicitly declared `READ ONLY` with 15–20-second statement timeouts.
- Worker release observed: `c0bc57c66aa3`. It predates the three latest coverage-workflow commits; production findings and current-source findings are identified separately.
- GitHub evidence includes actual merged-PR deployment jobs, manual dispatches, the automatic-deploy variable, and associated-PR API responses.
- Production was inspected without replaying, correcting, restarting, deploying, or changing data. Full exports, contacts, payloads, credentials, and generated production reports are excluded from these documents.
- Counts are time-specific, not a complete accuracy study. A missing structured field does not by itself prove a parser error. A healthy connection and current source head do not prove archive convergence.

## Workable epic map

| Requested area | Authoritative work | First deliverable | Order |
| --- | --- | --- | --- |
| 1. New-offer ingestion | [E24 — Automatic ingestion recovery](../epics/E24-automatic-ingestion-recovery/README.md) | Original archived event reaches a terminal outcome exactly once; fair catch-up resumes | Immediate |
| 2. Parser improvements | [E25 — Parser quality and automatic recovery](../epics/E25-parser-quality-and-automatic-recovery/README.md) | Source-evidence benchmark and deterministic repair of the confirmed price gap | Next; discovery can start immediately |
| 3. Map dots | [E26 — Automatic location validation and repair](../epics/E26-automatic-location-validation/README.md) | Address agreement and honest precision replace confidence-only acceptance | Immediate alongside E24 |
| 4. Stubs and misleading checks | [E14 — Production hardening](../epics/E14-production-hardening-and-scalability/README.md), T1/T2/T5 | Real browser/API/PostGIS/WebGL coverage and explicit legacy-route disposition | Alongside corrective work |
| 5. Code improvements | E14-T3/T4/T7 | Characterize orchestration behavior, then separate it and bound full-history reads | After relevant regression coverage |
| 6. Slow releases | [E27 — Faster verified releases](../epics/E27-faster-verified-releases/README.md) | Timed stages, shared verification, bounded release locking, automatic outcome reporting | Independent workstream |

All new tasks use P1 in the repository's priority vocabulary: required for safe production. “Immediate” expresses audit urgency, not an assertion that approval gates have already passed. E24-T1 should precede broad parser or location backfills so repairs do not compete with the replay loop.

## Verified checks

| Command / inspection | Result | What it establishes and what it does not |
| --- | --- | --- |
| `make install` | Passed; frozen Python and pnpm dependencies | Existing locked dependency graph installed; no production dependency added |
| `make format-check` | Passed | 306 backend files and frontend formatting |
| `make lint` | Passed | Ruff, ESLint, 17 import contracts; root deployment scripts are checked separately in CI |
| `make typecheck` | Passed | Strict Python check on 284 files and TypeScript check |
| `make contract-check` | Passed | OpenAPI drift, generated types, schema lint, and static documentation |
| `make test` | Passed | 803 backend tests including PostGIS integration; 169 frontend tests across 28 files |
| Backend coverage inside `make test` | 90.28% | Clears 90% aggregate gate; not a proof of production completeness |
| Frontend coverage inside `make test` | Lines 95.76%; branches 90.14% | Clears both floors; map-explorer branches are only 78.52% |
| `make test-e2e` | 10 passed, 2 skipped | Chromium, mocked API, map disabled; attribution-overlap cases skipped |
| `python3 -m unittest discover -s scripts -p 'test_*.py'` | 146 passed | Existing repository/deployment script unit tests |
| `make production-proof` | Passed | Existing local topology, release gate, rollback, shared-edge fixture/runtime, shell, and Caddy proofs; not a new live rollback rehearsal |
| `python3 scripts/check_markdown_links.py` and `git diff --check` | Passed | Documentation targets and whitespace |
| New workflow metadata/dependency validation | Passed | 26 workflow files, fourteen proposed tasks, pending approvals, and an acyclic 22-task dependency closure; existing unrelated YAML failure noted in Q3 |
| Existing parser applied in memory to masked Ostrzycka public text | Confirmed gap | Current e2-v13 still returns no price and no included-storage value |
| Production container/worker status | Containers healthy, source runtime head caught up | Does not establish media recovery, passive edit/delete acceptance, or archive completion |

Backend tests emitted three warnings: one HTTPX per-request-cookie deprecation and two SQLAlchemy connection-cleanup warnings. These are actionable test-fixture/resource-lifecycle evidence, not proof of a production connection leak. Browser runs also emitted environment color warnings. The suite is passing, not warning-free.

Local logs are under `/private/tmp/wef-audit-*.log`; they are not committed. The first inline parser invocation omitted required `edited_at` and failed before parsing; rerunning with the required value produced the recorded result. This was an audit invocation error, not a repository test failure.

## Findings and evidence

### I1 — Confirmed archive replay starvation; highest operational urgency

Production had 27,631 never-attempted new archive rows and 235 rows with a failed outcome. The eligible pending queue, which also includes retryable failures, contained 27,656 rows; the oldest timestamp was 2026-08-15. Exactly 25 pending rows had a terminal sibling for the same channel/message/event kind with a different checksum. Three sampled sibling rows had each been marked processed more than 20,000 times. One aggregate showed 152,064 successful live runs in the preceding 24 hours.

The path explains the evidence:

1. [RawEventDrainer](../../apps/backend/src/wef_backend/features/ingestion/application/raw_archive.py) reconstructs a live message from an archived payload, losing original media/entity fields.
2. [live_message_payload](../../apps/backend/src/wef_backend/features/ingestion/application/telegram_live.py) adds `from_live` and creates a different payload/checksum.
3. [LiveTelegramEventProcessor](../../apps/backend/src/wef_backend/features/ingestion/application/telegram_events.py) lands and completes that reconstructed row.
4. The drainer only marks the original `record.id` on failure, not on success. [The archive store](../../apps/backend/src/wef_backend/features/ingestion/infrastructure/raw_event_archive.py) keeps selecting the oldest 25 original rows.
5. The worker logs “drained” using attempted record count; activity can therefore look healthy while the backlog does not move.

This is backed by both live row metadata and source control flow. It does not mean all pending events are missing listings: historical records already exist canonically and many events are media/non-offer records. Fix acknowledgement identity, preserve source evidence, and reconcile outcomes before retrying the whole queue. Owner: E24-T1/T4.

### I2 — Conflicting checkpoint views and retry exhaustion

The redacted worker status reported durable checkpoint 29693, persisted maximum 29713, and runtime local/remote head 29713 with `remote_gap=false`. All 235 failed archive rows reported `RunLockHeldError`; their maximum attempt count was five, but the aggregate does not establish that every one is exhausted.

[RawEventDrainer](../../apps/backend/src/wef_backend/features/ingestion/application/raw_archive.py) reads the durable cursor before acquiring the shared processing lock. [latest_live_checkpoint](../../apps/backend/src/wef_backend/features/ingestion/infrastructure/telegram_worker_status_store.py) chooses the latest finished run rather than a durable channel high-water record. That combination permits stale replay work to publish a lower cursor. The observed mismatch is confirmed; the precise interleaving needs a deterministic regression test. Lock contention should defer with backoff rather than consume the same failure budget as malformed data. Owner: E24-T2.

Polling revisits only the configured overlap; old edits and deletes missed during downtime need explicit coverage/reconciliation semantics. E8's remaining passive edit/delete acceptance evidence stays in E8/B-003, rather than being silently marked complete by this audit.

### I3 — Media recovery is not guaranteed by successful message replay

The live processor marks raw/canonical work processed before media work, then skips media on `MessageOutcome.UNCHANGED`. The existing `test_unchanged_replay_skips_live_media_pipeline` explicitly asserts that skip. Reconstructed archived events also omit media descriptors. A crash after the canonical commit can therefore leave media work without a retry through this path. This is a source-confirmed recovery gap; this audit did not inject a production failure or quantify missing production assets.

[LiveMediaPipeline](../../apps/backend/src/wef_backend/features/ingestion/application/live_media.py) already has media replay keys. Use a separately durable media-work outcome and automatic retries; unchanged message content must not imply completed derivatives. Owner: E24-T3.

### P1 — Confirmed source-evidenced parser misses

Ostrzycka offer `4b148de5-ef94-432c-a466-3c872519e83b` contains a labeled apartment price of PLN 780,000 with a second EUR-denominated quote. The public API has no price. Current e2-v13 also returns no price when run on its masked public text. The source includes storage in the price, but the current parser returns no included-storage value. Area 37.50 m² does parse. A rooms warning is also produced and must be assessed against the source, rather than suppressed to make coverage green.

[extraction.py](../../apps/backend/src/wef_backend/features/ingestion/application/extraction.py) uses a closed set of label spellings and separator patterns; `Цена апартамента:` is outside the present price label family. Handling the label alone is insufficient: the money parser must distinguish alternative currencies from a same-currency amount range, add-ons, and price per square metre. Preserve the source's PLN amount as 78,000,000 minor units; do not derive an exchange rate.

The Jugosłowiańska example retains the correct supplied PLN 1,399,000 price and PLN 39,000 parking value. Those values must survive any parser or location repair. Owner: E25-T1/T2.

### P2 — The issue ledger is not a trustworthy count of missed offers

Across 3,320 visible offers, 982 lacked price, 364 area, 513 rooms, 624 had unknown market type, and 603 unknown property type. These overlapping counts size benchmark cohorts; they are not all parser defects because some source messages omit those values. The public map snapshot had 3,269 matching offers in its requested viewport, so that viewport is not the denominator for database-wide completeness.

Production held 25,548 `parser_miss` rows, 25,305 unlinked, and 3,520 `parser_incomplete` rows. These are ledger rows across messages/revisions/versions, not distinct missed listings.

[issue_outcome_for](../../apps/backend/src/wef_backend/features/ingestion/application/parse_issue_serialization.py) calls every non-candidate a parser miss, including expected non-listing content. It calls a listing incomplete only when warnings exist; silently absent fields may produce no warning. Unchanged messages also skip issue insertion. This both floods the recovery queue and hides some real missing-field cases.

Separate expected media/service/non-offer records, source-absent fields, source-evidenced extraction misses, conflicts, and provider failures. Measure eligible unique source revisions and field accuracy before spending AI quota. Owner: E25-T1/T3.

### P3 — Parser and geocoder improvements do not automatically repair history

Of 3,334 canonical offers, 3,294 still recorded e2-v11 and only five e2-v13. The remainder were 15 AI-parse, 15 operator-manual, and five synthetic records. These five synthetic rows were counted across all visibilities; this does not prove they are publicly visible.

The three inspected geocode selections still use `warsaw-address-v1` / `forward-geocode-v1` while current code is version 2. Existing commands allow operator replay/backfills, but routine convergence is not established. E21's documented AI fallback is owner-triggered generate/apply; having a batch CLI does not make it an automatic recovery service.

Automate version-aware, bounded reprocessing with durable progress, protected owner/AI fields, field-level provenance, stable offer IDs, and a second-run no-op check. New parser writes must refresh extraction provenance even when source revision is unchanged; the ordinary upsert only inserts a new offer-source extraction record when that source link is absent. Owners: E25-T4 and E26-T2.

### M1 — Both reported map cases have weak location evidence

| Case | Public location ID | API point, longitude / latitude | Stored precision / score | Selected provider result |
| --- | --- | --- | --- | --- |
| Gocław / Ostrzycka, 11 Apr 2026 | `373861ab-6214-4bf3-81c6-d9bd4c10c9ab` | 21.0805269 / 52.2342096 | Street / 0.50 | Ostrzycka, Warsaw |
| Gocław / Jugosłowiańska, 28 Jan 2026 | `8df1fc76-a8d6-466a-93d2-c33b146026da` | 21.091919 / 52.225418 | District / 0.48 | Gocaw, Warsaw |
| Additional Jugosłowiańska case, 11 May 2026 | `c09efdbc-5f58-4184-a5a0-86d8201f6cf6` | 21.068753 / 52.2463822 | Building / 1.00 | Praga-Południe-Ratusz, Grochowska, Warsaw |

The January Jugosłowiańska result is a neighborhood point, not a street result. The May result explicitly disagrees with the requested street. Ostrzycka's provider does name the correct street; without a building number or authoritative street-geometry comparison, this audit cannot assert a corrected exact point or conclude that its street representative point is geographically wrong. It is unsuitable as an implied exact building position.

The [municipal Gocław planning document](https://architektura.um.warszawa.pl/documents/12025039/19717181/MPZP_Goclaw_-_opis_wariantowych_koncepcji.pdf/519cc47c-2092-8c20-bdb9-f945e896fa8b?t=1634497936884) identifies the area within Praga-Południe and discusses Jugosłowiańska. The [city map and WFS directory](https://mapa.um.warszawa.pl/) provide a primary reference for the future street-geometry benchmark. This report does not invent rooftop coordinates from those references.

The first two rows have `manual_accept` / `ad-034-accept-pending-pins` lineage. [The recurring worker](../../apps/backend/src/wef_backend/recurring_geocode_worker.py) invokes this broad acceptance path automatically, so the lineage does not prove an individual human reviewed each point. [AD-034](../workflow/AUTONOMOUS_DECISIONS.md#ad-034-accept-in-scope-pending-geocode-pins-for-public-map-coverage) originally prioritized historical map coverage and explicitly acknowledged coarse points.

In the sampled public viewport, 345 of 2,190 map features were city/district precision (207 + 138); 600 were low confidence and 949 had no canonical district. These sets overlap and are not counts of wrong locations. Owners: E26-T1/T2/T3.

### M2 — Acceptance checks scope and score, not street agreement

[review_geocode_result](../../apps/backend/src/wef_backend/features/ingestion/domain/geocoding.py) accepts building/street results within a wide rectangular scope with confidence at least 0.80. It cannot compare a provider result to the source query. [The provider mapper](../../apps/backend/src/wef_backend/features/ingestion/infrastructure/geocoder_adapters.py) takes the first result, maps amenities to building precision, and retains little structured match evidence. Then [pending-pin acceptance](../../apps/backend/src/wef_backend/features/ingestion/infrastructure/accept_pending_geocode_pins_adapter.py) overrides low-confidence/low-precision review states.

Current display normalization also renders the examples as `ul. Ostrzycka, Gocław` and `ul. Jugosłowiańska, Gocław`: an unrecognized neighborhood is classified as an “other city,” omitting Warsaw from display. The geocoding query does append Warsaw, so display and geocode normalization are different defects.

Recommend automatic address decomposition, constrained candidate retrieval, street/house-number/district agreement and ambiguity checks, then confidence thresholds. A street-only source must remain street-level. If reliable resolution fails after bounded automatic attempts, preserve list visibility and explicit uncertainty; do not silently manufacture a precise dot. Owner: E26.

### Q1 — There is a real inert legacy endpoint, but fixture adapters are not the catalog

`GET /api/v1/estates` is explicitly deprecated and wired to [RetiredEstateQueryAdapter](../../apps/backend/src/wef_backend/features/estates/infrastructure/retired_adapter.py), which always returns an empty sequence. It is a compatibility remnant of E0, not the real map backend. Decide its supported lifetime and remove/version it only after contract-consumer evidence.

Production composition wires SQLAlchemy catalog adapters, the live worker wires Telethon, and recurring geocoding wires Geoapify. Fake Telegram clients, FixtureGeocoder, synthetic catalogs, and map placeholders have valid testing/loading roles; this audit found no evidence they replace production map ingestion. Document reachable test-only switches and reject accidental production use. Owner: E14-T1/T2.

### Q2 — Browser checks bypass the system responsible for wrong dots

[Playwright helpers](../../apps/web/e2e/helpers/catalog-mocks.ts) intercept `/api/v1/**`. [CI](../../.github/workflows/ci.yml) and `make test-e2e` build with `NEXT_PUBLIC_WEF_DISABLE_MAP=1`. Only Chromium is configured. Two attribution checks skip without a real canvas. Passing these tests does not exercise actual API-to-PostGIS projection, provider matching, live map selection, or WebGL clustering.

Keep component mocks for focused tests, and add a required small real-stack/WebGL journey with deterministic provider responses and real persisted coordinates. E14-T5 already owns that implementation; E24/E25/E26 supply their regression cases. E14-T2 owns targeted warning/resource-lifecycle fixes and critical-path quality floors.

### Q3 — Existing workflow metadata can be malformed while link checks pass

The strict YAML read used to verify the new roadmap found an unterminated quoted completion-evidence value in [E18-T2](../epics/E18-owner-location-verification/tasks/E18-T2-location-admin-console.md), line 56. It is present in the unchanged baseline and outside the new tasks' dependency closure. Existing Markdown link checks pass because they check paths, not workflow schemas. New E24–E27 metadata and their dependency closure were validated separately and pass.

E14-T1 should add workflow-schema and gate/reference validation with a malformed-evidence negative fixture; preserve historical owner approval evidence when correcting syntax. The audit does not silently alter the completed task's record.

### C1 — Improve measured hotspots, retaining the existing architecture

Current file sizes: extraction 1,225 lines, ingestion persistence 1,002, map explorer 1,130, admin views 906. Size alone is not a defect. The useful boundaries are text-field extraction, transactional persistence, provenance synchronization, archive/media completion, URL/query/selection state, and admin presentation.

The live event queue has no configured bound. [LiveMediaPipeline](../../apps/backend/src/wef_backend/features/ingestion/application/live_media.py) requests full-channel source anchors and existing replay keys for each media-bearing message; [the repository](../../apps/backend/src/wef_backend/features/ingestion/infrastructure/complete_import_repository.py) materializes those sets. Establish representative query-count/memory budgets, replace full-history reads with bounded lookups where measured, and test overload recovery before introducing a new queue dependency.

Use E14-T3/T4/T7, with E24 owning corrective ingestion behavior. Do not implement the same replay repair under an unrelated refactor branch.

### R1 — Most measured deployment time is outside activation

Job durations below come from successful deploy jobs on actual merged-PR releases. Queue time is run creation to first job start; inter-job scheduling accounts for the remaining elapsed seconds.

| PR / run | Run elapsed | Initial queue | Verification | Publish images | Deploy job |
| --- | --- | --- | --- | --- | --- |
| [#322 / 33774830809](https://github.com/Flippylolz/WEF/actions/runs/33774830809) | 10m36s | 4s | 7m05s | 1m37s | 1m27s |
| [#321 / 33676028013](https://github.com/Flippylolz/WEF/actions/runs/33676028013) | 9m31s | 4s | 5m33s | 2m14s | 1m26s |
| [#317 / 33670234372](https://github.com/Flippylolz/WEF/actions/runs/33670234372) | 14m48s | 5m37s | 5m55s | 1m38s | 1m17s |

The corresponding merge-to-run delay was only 2–4 seconds. These are three examples, not a population p95.

[Release workflow](../../.github/workflows/deploy-production.yml) is serialized as resolve → verify → publish → deploy. Its concurrency group covers the entire workflow. Verification installs dependencies on the host and then rebuilds/runs Compose test images; it also starts a host PostGIS service although tests use the Compose database. Backend/frontend tests and backend/web publishing run sequentially. Main pushes separately launch [CI](../../.github/workflows/ci.yml), duplicating much verification/build work.

The [manual c0bc57c run](https://github.com/Flippylolz/WEF/actions/runs/33791148422) took 20m31s: 7m55s before resolve started, a further 5m03s between resolve and verify, 5m29s verification, 40s publishing, and 74s deployment. A paired push run occupied the same production concurrency group first; the additional scheduling gap is observed but its cause is not established.

Prioritize queue scope, duplicate work, equivalent reusable checks, warm caches, and parallel independent jobs. Do not remove tests or health/rollback gates to meet a timer. Owner: E27.

### R2 — Green workflow does not imply deployed SHA

`AUTO_DEPLOY_ENABLED` was true. GitHub returned no associated PR for `9fc612f` and `c0bc57c`. The [latest push run](https://github.com/Flippylolz/WEF/actions/runs/33798049432) finished successfully after 7m15s but skipped its deployment job. The source gate intentionally rejects automatic deployment of unassociated direct pushes; manual dispatch of c0bc57c subsequently deployed.

Keep this safety boundary. Make outcome reporting distinguish verified-only, queued, deployed, superseded, and failed. Ordinary releases should originate from merged PRs and need no second dispatch; emergency dispatch should be idempotent for an already verified exact SHA and should not trigger another full queued copy unnecessarily. Owner: E27-T1/T2.

## Automation contract across every epic

The owner's instruction is to minimize manual work and use it only in extreme cases.

- No routine per-offer approval, daily command, parser-version replay dispatch, geocode acceptance click, or second deploy dispatch.
- Automatic recovery uses durable identity, bounded retry/backoff, quotas, leases, version checks, and safe pause/resume. Restarts must preserve progress.
- Automatically separate irrelevant source content and genuinely absent facts from repairable extraction failures. Never use higher apparent completeness as permission to invent values.
- AI proposals require source evidence, supported units/currencies/enums, revision checks, and calibrated validation. Model-reported confidence alone is insufficient.
- Automatically repair unambiguous points. If the source only supports an area/street, publish that precision honestly; unresolved records remain discoverable without implying an exact building.
- Escalate only after bounded automatic recovery cannot resolve a material ambiguity, repeated systemic failure, credential/access loss, a protected-value conflict, or a destructive recovery decision. One actionable incident should replace repeated per-row notifications.
- Track unique work completed, queue age, retry/exhaustion, field accuracy, location agreement, release outcome, and human interventions. Progress means reconciliation, not merely successful process exits.
- Preserve source evidence, contacts protections, owner-verified corrections, audit lineage, immutable release digests, health-gated activation, and rollback. Existing backups remain deferred under ADR-015; deploy rollback is not data recovery.

## Sequencing and non-duplication

1. Refine E24-T1 and E26-T1 first; existing task-specific regression tests belong with those corrective changes.
2. E25-T1 benchmark discovery and E27 release work can proceed independently.
3. After E24-T1, run durable bounded parser/geocoder remediation through E25-T4/E26-T2, with accepted policy and preserved provenance.
4. E14-T1/T2/T5 own shared check truthfulness, critical coverage, and real-stack browser infrastructure. E14-T3/T4/T7 own general maintainability and capacity. E24-T4 supplies ingestion progress signals; E14-T6 owns broader observability infrastructure.
5. E8/B-003 still owns passive event acceptance. E7-T5/E14-T9 still own backup/restore capability. E27 performance work must preserve E14-T8 release-integrity scope.

E14's pending implementation plan predates these findings. Use this report as refinement input, and follow the repository's revision/invalidation rules before materially changing its approved spike or promoted tasks. Do not create duplicate authoritative E14 task files here.

New epic spikes are researched revision-1 proposals awaiting owner decision; tasks remain in `proposed-tasks/` with `actionable: false`. Implementation-plan files are deliberate empty draft shells until spike approval and task promotion. That workflow state records future implementation gates; it did not block completing the requested audit and epic definitions.

The [changed-file manifest](2026-09-05-files.md) lists every documentation file in this handoff.
