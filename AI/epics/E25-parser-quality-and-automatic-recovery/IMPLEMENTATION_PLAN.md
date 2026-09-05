---
schema: ai-workflow/implementation-plan@1
epic: E25
title: "Parser quality and automatic recovery"
status: awaiting_approval
revision: 2
owner: owner
spike_revision: 2
task_sequence:
  - id: E25-T1
    revision: 1
  - id: E25-T2
    revision: 1
  - id: E25-T3
    revision: 2
  - id: E25-T4
    revision: 1
approval:
  required_role: owner
  status: pending
  decided_by: null
  decided_at: null
  approved_revision: null
  evidence: null
invalidation:
  invalidated_by: Codex
  invalidated_at: "2026-09-05T11:12:47Z"
  reason: "Groq Batch application-state retention conflicts with the required Zero Data Retention boundary; review queued synchronous transport."
  return_to: spike

---

# Implementation plan: Parser quality and automatic recovery

## Revision 2 decision requested

Revision 1 was approved under AD-048. Revision 2 awaits explicit approval together
with spike revision 2; neither artifact restores task gates before that decision.
The [provider amendment](PROVIDER_PRIVACY_REVISION.md) records current official
evidence, rejected alternatives, exact transport/state changes and validation.
T1 and T2 remain behaviorally unchanged and retain their published test evidence.
No implementation code has been written for T3.

## Historical approved baseline

The owner approved [spike revision 1](SPIKE.md) on 2026-09-05 in response to the explicit spike-approval question; [AD-047](../../workflow/AUTONOMOUS_DECISIONS.md#ad-047-approve-e25-spike-revision-1-and-prepare-the-implementation-plan) records the decision. The owner approved implementation plan revision 1 by replying “continue” directly to its approval request; AD-048 records the scope. Task dependency and branch gates remain enforceable.

Research baseline: main `a2cdb16`, fetched 2026-09-05. The [audit](../../audits/2026-09-05-system-audit.md#p1--confirmed-source-evidenced-parser-misses) confirms the Ostrzycka label/storage gaps, the misleading parse-issue taxonomy, and stale historical parser versions. Its production counts are dated observations, not a new measurement or a field-accuracy benchmark.

The intended outcome is evidence-backed extraction and routine automatic recovery. Backend application services retain mutation authority; no new production dependency, provider/model, paid usage, deployment topology, geocoder behavior, or public visibility policy is introduced. Automatic recovery means validated data processing after a reviewed parser release, not autonomous modification of parser code.

## Ordered task sequence

T1, T2 and T4 retain revision 1. T3 advances to revision 2 for the transport change; its original acceptance criteria are retained. Each implementation uses its own branch/PR. The planning branch contains documentation only. Execute T1 → T2 → T3 → T4; this serial order simplifies review without adding a T2 dependency to T3.

| Task | Dependencies and gate | Independently reviewable result |
| --- | --- | --- |
| [E25-T1](tasks/E25-T1-benchmark-source-evidence-and-triage.md) | None; revision 2 gate revalidation pending | Safe benchmark, source-evidence classification, issue lifecycle and recovery eligibility |
| [E25-T2](tasks/E25-T2-repair-deterministic-extraction.md) | E25-T1 done or valid ancestor PR | Deterministic money/storage/rooms fixes with benchmark and persistence evidence |
| [E25-T3](tasks/E25-T3-automate-validated-ai-exceptions.md) | E25-T1 done or valid ancestor PR | Durable scheduled AI proposals, evidence validation and guarded automatic application |
| [E25-T4](tasks/E25-T4-converge-parser-versions-automatically.md) | E24-T1, E25-T2, E25-T3 done or valid ancestor PRs | Version-aware historical convergence, protected provenance and restart-safe replay |

[E24-T1](../E24-automatic-ingestion-recovery/proposed-tasks/E24-T1-terminate-original-archive-work.md) is still proposed on this baseline. E25 approval does not authorize E24 implementation or bypass its gate. T1–T3 may proceed after this plan is approved. T4 cannot begin until all dependencies have completion evidence or satisfy the repository's strict ancestor-PR stacking rules; all dependencies must be done before T4 completion/merge. If E24 changes the replay interface materially, revise this plan before T4 implementation.

### T1: Establish an evidence baseline and truthful recovery eligibility

Affected modules: ingestion `application/parse_issue_serialization.py`, `domain/parse_issue.py`, `infrastructure/parse_issue_store.py`, `infrastructure/parse_issue_backfill.py`, persistence models, and admin parse-issue reporting/selection. Add the benchmark beside the existing sanitized extraction corpus, with evaluation in the existing backend test suite.

Create a versioned corpus of at least 60 invented or safely anonymized source equivalents, with at least five cases per applicable template/language stratum and at least 15 negative media/service/non-offer cases. Include both reported listings, alternative currencies, true ranges, per-area amounts, add-ons/inclusion, rooms tags, multilingual market/property types, conflicts, and silent misses. Record label provenance as synthetic or audit-derived, never claim invented fixtures establish production prevalence. Ambiguous labels remain unresolved and are excluded from exact-value scoring with their count reported.

For each supported field, retain expected typed value, currency/unit, presence/absence, and exact supporting span. Report exact-value accuracy over source-evidenced labels, false positives over absent/negative labels, candidate precision/recall, source-absent rate, and unresolved count. A separate restricted read-only sample may establish production representativeness; publish only aggregate strata/counts. Missing source access limits production acceptance, not safe fixture implementation.

Keep existing issue outcomes readable. Add an orthogonal classification and lifecycle: expected non-offer/media, source absent, extraction miss, incomplete, conflicting, provider failure; open/resolved/superseded. A field-evidence detector recognizes supported labels independently of whether the extractor emitted a warning. Unknown formats remain unresolved rather than being asserted absent. Recovery requires listing evidence and a supported repairable gap; all non-candidates must not automatically become AI work.

Deduplicate by source revision, parser version, policy version and field/reason identity. Keep original issue history, append transitions, and resolve repairable issues transactionally after a newer successful extraction. Backfill classifications in bounded keyset batches; historical unknowns stay explicitly unclassified until evaluated. Compare old/new selection counts in observation mode before using the new eligibility selector.

Tests: silent labeled miss, absent field, non-offer, contradictory evidence, duplicate encounter, unchanged replay, later successful version, edit superseding an issue, and migration compatibility against real PostGIS. Update `AI/data/QUALITY_AND_READINESS.md` and `AI/ingestion/PIPELINE.md` with definitions and denominators.

### T2: Repair deterministic extraction and money semantics

Affected modules: ingestion `application/extraction.py`, typed extraction domain values, the existing sanitized corpus and `test_listing_extraction.py`; persistence/catalog tests verify the final stored and filtered values. Reuse decimal/minor-unit conversion rather than introducing float arithmetic.

Add evidenced label and inclusion variants, including `Цена апартамента:`. Parse amounts with their own currency and semantic role before choosing the apartment price. Prefer the explicit PLN apartment quote when paired with an EUR alternative; never infer an exchange rate or combine different currencies into one range. Same-currency ranges require a range connector and matching role/unit. Per-area and parking/storage amounts remain separate from apartment price. Conflicting unresolvable quotes remain unapplied and classified with their evidence.

The Ostrzycka equivalent must produce 78,000,000 PLN minor units, 37.50 m², included storage and the source-supported rooms result. The Jugosłowiańska equivalent must retain 139,900,000 apartment and 3,900,000 parking PLN minor units. Resolve tag/label agreement without suppressing genuine contradictions.

Increment `PARSER_VERSION` once for the accepted coherent fix and carry that version through extracted provenance; allocate its exact next value from current main at implementation time. Require zero new benchmark false positives or regressions in previously correct fields and fixes for both reported examples. Run an aggregate read-only historical diff before T4 application. T2 changes extraction for new processing; T4 owns automatic historical scheduling.

Tests include malformed/grouped numbers, conflicting currencies/units, genuine ranges, per-area values, inclusion versus separately priced storage, tag/label agreement and disagreement, database minor-unit persistence, and public price/filter projections. Update `AI/ingestion/PIPELINE.md` and the quality baseline with measured results.

### T3: Automate only validated AI exceptions

Affected modules: admin `application/ingestion_ai_parse.py` and offer-enrichment validation, application-owned provider ports, `infrastructure/ingestion_ai_parse_store.py`, Groq batch transport, the batch command, persistence models and worker composition. Extract reusable application services where necessary; ingestion must not import admin interface or infrastructure. Keep manual commands as an exceptional repair route.

Existing ADR-022 requires owner batch initiation. T3 must record a narrowly scoped ADR amendment for standing scheduled authorization and next-window retry of eligible parser exceptions before enabling that behavior. The implementation approval requested here includes that amendment within the approved E25 automatic-recovery scope. Place review remains owner-confirmed. Provider/model, privacy, missing-only writes and budget ceilings stay fixed; changing them returns to spike review.

Use the existing Groq `openai/gpt-oss-20b` single-item Chat Completions port with verified Zero Data Retention. A local durable cohort replaces provider Batch/Files transport; update ADR-022 as specified in the provider amendment. Store durable work identity `(source_revision, parser_version, policy_version, prompt_schema_version)` and its current missing-field set. Persist claim/lease, attempt count, next eligible time, local cohort/item/attempt IDs and returned provider request IDs, quota reservations, minimized failure reason and apply outcome. After restart, resume locally queued work and reconcile locally saved proposal/apply outcomes. A submitted synchronous request has no remote job to poll: an expired submitting claim without a saved result becomes an uncertain-submission exception and is never automatically resent. Existing remote Batch jobs, if any, require the already-authorized reconciliation path and cannot be silently migrated or resubmitted.

Only T1-eligible current revisions enter this queue. Already resolved/source-absent/irrelevant/invalid cases do not cause repeat calls. For existing offers, automatic fills use the existing ADR-022 offer-field allowlist (market type, currency, apartment/parking/storage money and inclusion, area, rooms, floor and delivery); property type remains deterministic in this revision. Require a unique non-contact source span, semantically valid value/units, current source and offer snapshot, and a still-missing field. Confidence and a matching text fragment alone cannot establish semantics.

For an unlinked confirmed listing, use the existing ingestion recovery creation path only after the complete validated proposal satisfies the normal candidate, deduplication and source-link rules. Reuse current recovery visibility and location policy; the model cannot choose visibility, relationships, contacts, coordinates or identity. Never create a second offer when another worker linked the source. Owner/AI-protected or already known values are not overwritten; protected conflicts produce one minimized exception.

Validate each auto-enabled field family against at least ten supported positive and ten negative/conflict benchmark cases, with zero unsupported applications and 100% correctness among applied cases. A family without that evidence remains observation-only. This finite test gate is not a claim of universal model accuracy. Fake-provider tests are mandatory; real-provider calibration and the representative acceptance window require existing authorized credentials/privacy settings and remain within the same budget.

Update `AI/operations/OPERATOR_COMMANDS.md`, the ingestion pipeline, security/AI documentation and ADR-022 with actor attribution, scheduling authority, eligibility, pause/resume and uncertainty handling. No raw prompt/provider response is logged or committed.

### T4: Converge history with correct provenance

Affected modules: ingestion `application/raw_replay.py`, `infrastructure/persistence_adapter.py`, archive selection/models, field-origin persistence, worker composition and operator reporting. Reuse the E24-T1 original-event completion contract after its gate clears. Keep parser version distinct from immutable source revision.

On startup and periodic maintenance, compare persisted per-source evaluation versions with the deployed accepted parser/policy version. Create bounded durable work only for stale eligible current revisions. Select with keyset pagination; complete/retry/terminal states prevent a repeatedly unrepairable first page starving later work. Record exclusions for operator/synthetic/unsupported legacy sources; count them separately from eligible convergence.

Compute outside a short write transaction, then recheck the current source revision and protected origin/value snapshot under lock before applying. In one transaction update only eligible fields, refresh offer-source extraction provenance even for unchanged source revisions, append field-level before/after origin/version/span events, advance the evaluation version and work state, and reconcile issue lifecycle. Successful evaluation with unchanged values still advances evaluation/provenance as appropriate; the next run causes zero canonical changes and no duplicate lineage events.

Do not blindly route historical data through an upsert that can reset unrelated state. Preserve offer IDs/favorites/source links, encrypted contacts, deletion/hidden state, media/location relationships, owner corrections and AI origins. Deterministic overwrites require an existing parser-owned value, unambiguous new evidence and a current snapshot; unknown legacy ownership is protected pending explicit classification. Changed source revisions supersede stale work and are scheduled independently.

Historical parsing does not invoke geocoding or media providers. It yields to live ingestion between bounded chunks and automatically resumes after contention/restart. A deployment version downgrade pauses convergence; an older parser must not schedule a reverse rewrite of newer evaluations.

Tests: parser-only changes on unchanged sources, source edit races, stale/reclaimed claims, interrupted transactions, fair retry selection, same-version second-run no-op, protected values, stable IDs/favorites/visibility/deletes/contacts, refreshed source/field provenance, and facet/filter consistency. Update pipeline and operations documentation with convergence counters and rollback ownership.

## Resource limits and failure handling

These are revision 2 application limits for approval, not claims about current external provider limits. Recheck provider/project eligibility at activation; a lower configured or provider limit always wins.

| Resource | Revision 1 limit and behavior |
| --- | --- |
| Maintenance cadence | Once per 60 seconds in the existing worker lifecycle; one active recovery owner per source, with durable leases/advisory locking |
| Classification/replay | At most 100 selected records per tick, transaction chunks of at most 10; yield after 5 seconds of work and between chunks; do not start historical work while live ingestion is unhealthy or has ready work |
| Replay canary | First 25 eligible records per accepted parser/policy release in read-only comparison; expand only after automated value/provenance/state invariants pass; insufficient backlog uses all available records and reports count |
| AI canary | First 10 eligible unique revisions in generate/validate observation mode; apply only after field-family benchmark and current-revision/protection checks pass |
| Provider quota | At most 20 item-generation reservations per UTC day shared with existing owner interactive/batch work; scheduler consumes that same owner allocation, never a fresh service-account allocation; zero paid-spend authorization |
| Provider request | Existing preflight maximum 5,500 input plus 1,500 output/reasoning tokens; whole masked descriptions only; one generation request in flight across manual/scheduled entry points; local cohorts at most 10 items; durably pace each request at least 60 seconds after the previous submission; reserve quota before every attempt |
| Transport | 30-second HTTP timeout per single-item submission; persist attempt ID and submit/result state; no network wait while holding canonical database locks |
| Retry | Local transient failures: persisted exponential delay from 60 seconds up to 1 hour; release claims between attempts. Provider 5xx or proven pre-submission timeout: at most one safe retry, quota-reserved; unknown post-submission timeout becomes uncertain and is not resent; after a second known-safe failure retain an actionable exception |
| Rate/quota limits | Persist eligibility no earlier than the later of Retry-After and the next UTC budget window; no automatic retry in the same window; reservation survives restart |
| Terminal failures | Invalid/fabricated evidence, refusals, protected conflicts, unsupported inference and non-recoverable access errors remain unapplied; no repeat generation for unchanged work identity |
| Leases | 120 seconds for local work, refreshed before expiry; persisted submit/result state survives a local lease; reclaim checks uncertain attempts and proposal/apply state before doing work |

The daily item quota includes requests that fail or have uncertain outcomes. Durable atomic reservation must cover every existing AI entry point so concurrent manual and scheduled work cannot exceed the shared ceiling. Existing owner cohorts use the same reservation ledger and single-item transport under ZDR. Durable shared pacing prevents concurrent manual/scheduled quota bursts. A failed resource preflight defers work without provider submission.

## Data, contracts and migration order

Use additive Alembic migrations. T1 owns issue classification/lifecycle and unique issue identity; T3 owns durable recovery jobs, provider reservations and local cohort/attempt correlation; T4 owns parser-release/evaluation progress and field-origin history. Reuse existing lineage and proposal tables where they meet these contracts instead of duplicating sources of truth. No source export or source text is copied into the new metadata tables.

Keep existing readers compatible: legacy outcome strings remain available while new fields are nullable/defaulted until backfilled. Database uniqueness enforces deduplication; source/offer snapshot guards prevent stale application. Deploy additive schema before new writers. Run backfills in bounded restartable batches; no table-wide rewrite or deletion of source/issue history. T4 must retain old value plus old/new ownership for every automatically changed field to support guarded rollback.

Public catalog response shape remains unchanged. If admin reporting changes OpenAPI, regenerate its committed contract/types and add compatibility tests. No frontend-only business logic or duplicated field parser is permitted. Generated migrations/tests/contracts are implementation work, not outputs of this planning change.

## Security and privacy

Reuse contact masking, server-only credentials, field allowlists, strict schema validation, immutable source evidence and minimized audit records. Treat source/provider text as untrusted data. Source spans must resolve uniquely in the current immutable revision and support the proposed interpretation. Never send encrypted contact fields, Telegram session data, raw archive payloads, account data or unrelated records to the provider.

AI scheduling remains disabled unless the current project has verified Zero Data Retention, authorized masked-text transmission, credentials and free allocation. Missing prerequisites produce a single actionable activation status, not endless provider retries. Implementation-plan approval does not itself verify those external prerequisites or authorize production provider enablement. No paid calls, new accounts or new production dependencies are included.

## Verification and evidence

Before every task push run `make lint` and `make test`. Run `make format-check`, `make typecheck` and `make contract-check` for affected scope; T1/T3 admin contract changes must exercise contract generation. Run repository Markdown links and required safety/architecture checks. Record exact commands/results and actual version/commit in each PR.

Use real disposable PostGIS for migrations, concurrency, checkpoint and provenance tests. Provider tests use deterministic fakes for timeout, 429, malformed JSON, fabricated spans, semantic contradictions, stale snapshots, duplicate attempts, unknown submission outcomes, restart and idempotent application. Verify database/public projection money units and filters in T2/T4. Shared cross-browser/WebGL infrastructure remains E14-T5's scope; supply E25 regressions without duplicating that epic.

Before automatic historical expansion, record read-only aggregate diffs, canary selection counts, protected-state invariants, and version distributions. For the eligible cohort, require a second unchanged-source/version run with zero canonical changes. Reconcile a mutually exclusive per-record outcome denominator: considered = source-absent + updated + unchanged + excluded + deferred + protected-conflict + failed; individual field reasons are reported separately to avoid double counting.

T3 acceptance includes a representative 24-hour window, extended across a second quota window when needed to exercise rollover. Report eligible unique revisions, applied/resolved/deferred/terminal cases, token/request use, actual provider spend if available, and human interventions. Routine eligible cases require zero per-offer actions. Do not mark the epic done based only on fake-provider tests or because missing credentials prevent live evidence; report the remaining activation/acceptance gate explicitly.

## Rollout, pause and rollback

Roll out T1 observation/classification → T2 tested extraction → T3 generate/validate canary → T4 read-only historical canary → bounded application. Parser/policy acceptance is a reviewed release artifact backed by benchmark results. Automatic canary checks stop expansion on unsupported writes, protected-state changes, duplicate identities or broken lineage; ordinary retries and completed batches need no owner dispatch.

Configuration belongs to existing backend/worker composition and release settings. Keep separate pause controls for classification/replay scheduling, AI submission and AI auto-application. Pause prevents new claims and canonical writes while preserving jobs/checkpoints for reconciliation. Resume only from durable state. An in-flight single-item response may finish and save its validated proposal while application is paused. No new generation starts during submission pause.

Stop new scheduling on regression. Roll back the runtime to its prior immutable release, keeping additive tables and audit history. Reverse an affected field only if both its current value and origin still equal the recorded automatic write; later owner/AI/source changes are preserved and reported as conflicts. Never restore whole tables, rewind source checkpoints, delete offer identities or downgrade newer parser evaluations automatically. Interrupted rollback is idempotent and itself audited.

No merge is authorized by this plan approval unless the owner separately requests it. Every required CI/review check must pass before any authorized merge. Production replay/provider enablement and acceptance require their recorded prerequisite evidence. ADR-015 backup deferral remains unchanged; this plan does not assert that persistent data is backed up.

## Risks and invalidation

- T1: an unlabeled or synthetic-only corpus can overstate accuracy. Separate exact regression confidence from production prevalence and record unresolved strata.
- T2: expanded labels can turn alternatives into incorrect ranges. Require role/currency/unit evidence and negative benchmark cases before accepting the parser release.
- T3: batching/retries can duplicate provider spend or apply stale evidence. Reserve quota durably, retain uncertain synchronous attempts without resubmission and guard every apply transaction; uncertain submissions remain exceptional.
- T4: unchanged-source replay can overwrite curated fields or retain stale provenance. Use protected origins and atomic field/extraction/progress writes with restart and race tests.
- T4: E24-T1 is unimplemented on this baseline. Retain the dependency and revise the plan if its final interface materially changes the replay design.

A new provider/model, paid allocation, broader automatic field/visibility authority, weaker privacy/protection rules, new production dependency or topology change returns to spike review. Material changes to task boundaries, dependencies, numeric budgets, schema ownership, acceptance, rollout or rollback require a new implementation-plan revision. Routine file placement within the named application boundaries and allocating the next unused migration/parser version are implementation details.

## Approval checklist

- [x] Prior spike revision 1 approval is retained; revision 2 resolves the provider premise.
- [x] All four sequence entries are promoted tasks with preserved acceptance/traceability; T3 advances to revision 2.
- [x] Dependencies are acyclic and enforceable; E24-T1 remains explicitly blocked.
- [x] Modules, contracts, data ownership, tests, limits, rollout and rollback are defined.
- [x] No new provider/dependency/spend decision is implicitly approved; existing activation prerequisites remain enforced.
- [x] No application code, tests, migrations or disposable proof code has been written.
- [x] Revision 1 approval is retained in AD-048 and Git history.
- [ ] Owner explicitly approves spike revision 2 and this implementation plan revision 2.
- [ ] Restore non-done task gates against approved revision 2 before resuming work.
