---
schema: ai-workflow/spike@1
epic: E17
title: "Raw archive replay and filter integrity research"
status: awaiting_approval
revision: 1
owner: owner
research_only: true
code_allowed: false
decision_ids:
  - ADR-006
  - ADR-012
  - ADR-021
domain_docs:
  - ../../ingestion/PIPELINE.md
  - ../../ingestion/GEOCODING.md
proposed_task_ids:
  - E17-T1
  - E17-T2
  - E17-T3
  - E17-T4
  - E17-T5
  - E17-T6
approval:
  required_role: owner
  status: pending
  decided_by: null
  decided_at: null
  approved_revision: null
  evidence: null
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# Spike: Raw archive replay and filter integrity research

## Question

How should WEF retain every incoming Telegram message verbatim inside the application
database, decouple canonical processing into a replayable background stage, harden the
parser against the channel's real template variants (currency words, grouped numbers),
and serve filter facets from a backend-owned canonical vocabulary — so an owner-supplied
data backup can be replayed and promoted to production as the epic's completion gate?

## Context and constraints

- PR #197 (`e2-v4`) fixed label-less pin-line location extraction and stopped geocoding
  the `Unknown location` sentinel, but checksum-unchanged messages are never
  re-extracted, so already-ingested rows keep stale extractions.
- The raw source of record today is the operator-staged Telegram Desktop export,
  mounted read-only into importer commands; the database stores source messages and
  revisions but couples them to canonical writes.
- Governance: large data reprocessing must be an explicit importer operation, never an
  Alembic data migration (`AI/operations/DEPLOYMENT.md`); the backend is authoritative
  for business behavior and the frontend renders generated contracts
  (`AGENTS.md`, ADR-012); no raw export/media enters Git.
- Geocoding stays Geoapify under ADR-021/D-002 quota controls; any replay must reuse
  the cache/budget machinery and the sentinel exclusion from PR #197.
- Live worker supervision, checkpoints, and reconciliation bounds from E15 must keep
  holding; E17 must not regress liveness or reconciliation SLAs.

## Research method

- Inspected `features/ingestion` (extraction, persistence, telegram events/backfill/
  reconciliation) and `features/catalog` (browse/map adapters, filter application).
- Reproduced the reported parser defect against the current parser on 2026-08-29.
- Inspected the frontend filter controls for client-side option derivation.
- No production code, scaffolds, migrations, or experiments were produced.

## Evidence

Verified facts (code references from `main` at `697c683`, 2026-08-29):

1. **Parser price defect reproduced.** `extract_listing` on a message containing
   `💸Цена:850 000злотых` yields `MoneyRange(850–850)` with `currency=None` plus an
   `unknown_currency` warning. `_NUMBER` in
   `features/ingestion/application/extraction.py` ends with `(?!\w)`, so the grouped
   form `850 000` fails when a currency word follows without whitespace, and the regex
   backtracks to the bare `850`. `_CURRENCY_PATTERN` recognizes only ISO codes and
   `zł/€/$` symbols, so `злотых` is untracked.
2. **Facets are raw text.** `SQLAlchemyBrowseAdapter` builds the district facet with
   `SELECT DISTINCT locations.district ORDER BY ...` over whatever the parser stored.
   The labeled `district` field stores unmodified source text
   (`persistence_adapter._resolve_location`), while the `e2-v4` pin-line path stores
   canonical names — so mixed canonical/raw/typo variants coexist and each becomes a
   separate filter option.
3. **Filter matching is exact and case-sensitive.**
   `LocationRow.district.in_(filters.districts)` in `map_query_adapter.py` (and the
   browse equivalent) means choosing `Praga PołUdnie` matches only that exact string;
   variants must be selected one by one.
4. **Canonicalization half-exists.**
   `canonical_warsaw_district` (NFKC + casefold) already collapses pure case variance
   (`BiałOłęKa` → `Białołęka`), but not hyphen loss (`Praga PołUdnie` vs
   `Praga-Południe`) or letter typos (`BiałOłęCka` folds to `białołęcka`, not
   `białołęka`). Those need a reviewed alias/reroute table — exactly the owner's
   "reroute those exceptions" instruction.
5. **No replay path.** Offers persist `parser_version`, but nothing selects stale
   versions; `RunMode.REPROCESS` is an unused enum value; `persist_batch` returns
   `UNCHANGED` on equal checksums without touching offers. Live extraction is
   synchronous inside `telegram_events.py`/`telegram_backfill.py`.
6. **Frontend behavior.** `map-filter-controls.tsx` merges backend facets with the
   current draft and sorts with `localeCompare` (locale-dependent ordering is a
   flakiness candidate); option values themselves are backend-provided strings.

Assumptions and uncertainty:

- The production database can absorb an append-only raw-event table plus a backlog
  replay without violating E14 capacity budgets; sizes must be measured on the
  owner-supplied backup during E17-T6 (assumed modest: ~27k historical messages plus
  a small live rate).
- Geoapify quota is sufficient for re-geocoding newly resolved locations after replay
  (cached queries are free; the distinct-address estimate is a few hundred).
- Whether edits must also archive intermediate revision payloads (they do today via
  `source_message_revisions`) — the raw archive must not lose them.

## Options considered

**Raw retention.**

- *New append-only raw-event table + background drainer (selected).* Land every
  new/edit/delete event verbatim with a checksum and processing ledger, then drain to
  canonical state in a background stage. Benefits: parser upgrades replay from the
  database; ingestion survives canonical-stage failures without losing source data;
  processing outcomes are observable per event. Costs: new table, worker stage, and
  retention policy.
- *Reuse `source_message_revisions` as the dump (rejected).* Coupled to canonical
  transactions, shaped around messages rather than events, and drops the
  processing-ledger/replay semantics needed for re-import.
- *Periodic export snapshots (rejected).* Not continuous, keeps the staging-file
  dependency, and still cannot replay without Telegram.

**Re-import.**

- *Replay the raw archive per parser version (selected).* Deterministic, checkpointed,
  no Telegram traffic, reuses existing upsert/reconciliation semantics.
- *Re-run the Telegram export importer (rejected as primary, retained as acceptance
  gate).* Requires a fresh owner-staged export each time; kept as the E17-T6
  completion evidence over the owner's new backup.
- *Wait for organic edits (rejected).* Indefinite and incomplete.

**Filters.**

- *Canonicalize at write + reviewed alias reroute + backend-owned facet vocabulary
  (selected).* Raw display text is preserved for lineage; only a canonical value ever
  reaches `locations.district`, facets, and matching; the alias table is reviewed data,
  versioned in the repository. Frontend renders backend options verbatim (minimal FE
  logic, per ADR-012).
- *Serve-time SQL normalization (rejected).* Hides bad data, leaves matching fragile,
  and spreads policy into queries.
- *Frontend dedupe/case-folding (rejected).* Duplicates business logic in the client
  and diverges from generated contracts.

## Recommendation

Proceed with the selected options as six proposed tasks: raw archive + background
processor (T1), parser-version replay command (T2), parser hardening for currency
words and grouped numbers (T3), backend-authoritative canonical filters with alias
rerouting (T4), filter test hardening (T5), and the owner-gated backup replay +
production promotion (T6). A new ADR covering "database-of-record raw replay" should be
drafted during implementation planning (it supersedes none of ADR-006/012/021; it
extends them).

## Proposed task boundaries

- **E17-T1 — Raw event archive and background processing.** Append-only raw-event
  table + drainer; live worker lands events first, canonical processing moves off the
  reconciliation hot path.
- **E17-T2 — Parser replay re-import.** Operator command that re-derives canonical
  offers/locations from the raw archive for a target parser version; idempotent,
  checkpointed, reuses geocode budget/sentinel guards.
- **E17-T3 — Currency-word and grouped-number parser hardening.** `злотых`-style
  currency words map to PLN (reviewed word list), grouped numbers survive adjacent
  currency words; fixture set from real channel samples.
- **E17-T4 — Canonical filter vocabulary and typo rerouting.** Write-time
  canonicalization, reviewed alias table (`Praga Południe` → `Praga-Południe`,
  `BiałOłęCka` → `Białołęka`), backend-owned facet contract, FE renders only.
- **E17-T5 — Filter determinism and test coverage.** Contract/unit tests for facets,
  parsing, matching, ordering, and URL round-trips; remove locale-dependent ordering.
- **E17-T6 — Owner backup replay and production promotion.** Completion gate: replay
  the owner's new data backup, verify quality metrics, promote, record evidence.

Dependencies: T2 depends on T1; T6 depends on T1–T5; T3/T4/T5 are independent of T1
and can proceed in parallel once promoted.

## Risks and open questions

- Raw-archive retention and growth policy (keep forever vs bounded window) — owner
  decision during implementation planning.
- Alias/reroute table ownership: reviewed in-repo list vs admin-managed table —
  recommend in-repo reviewed list for auditability; confirm with owner.
- Currency-word scope: PLN words only (`злотых/злотый/złotych`) or also
  `евро/долларов` — recommend PLN now, others only with fixtures.
- Background processor must not regress the E15 reconciliation liveness healthcheck;
  needs explicit liveness surface.
- Replay blast radius on offer visibility/dedup fingerprints — must reuse the exact
  revised-offer semantics so replay matches edit behavior.

## Invalidation triggers

- The channel or Telegram API changes message/edit delivery in a way the raw event
  shape cannot represent.
- ADR-012 (backend-authoritative) or ADR-006 (shared ingestion core) is superseded.
- Production capacity evidence shows the raw archive or replay violates E14 budgets
  with no mitigation.
- The owner changes the completion gate (backup replay + production promotion).

## Exit checklist

- [x] The question is answered within the stated scope.
- [x] Evidence and uncertainty are distinguishable.
- [x] Affected decisions and domain documents are linked.
- [x] Proposed task boundaries and dependencies are identified.
- [x] No production or disposable proof code was created.
- [x] `revision` represents the material content being submitted.
- [x] `status` is `awaiting_approval` and approval remains `pending`.

## Owner decision

The owner records the decision only in the YAML `approval` object. Approval of this
spike revision permits task refinement/promotion and implementation planning; it does
not permit code.
