---
schema: ai-workflow/task@1
id: E3-T3
epic: E3
title: "Implement geocoder abstraction and cache"
status: draft
revision: 2
priority: P0
size: L
milestone: M1
dependencies: [E2-T2, E3-T1, E3-T2]
requirement_ids: [P-001, P-007]
decision_ids: [ADR-005, ADR-012, ADR-021]
deferred_decision_ids: [D-002]
promotion:
  source: ../proposed-tasks/E3-T3-implement-geocoder-abstraction-and-cache.md
  promoted_by: "Cursor Agent (owner-authorized after spike revision 3 approval)"
  promoted_at: "2026-08-14T00:42:00Z"
spike_gate:
  status: satisfied
  file: ../SPIKE.md
  approved_revision: 3
  verified_by: "Cursor Agent"
  verified_at: "2026-08-14T00:42:00Z"
implementation_gate:
  status: blocked
  file: ../IMPLEMENTATION_PLAN.md
  approved_revision: null
  verified_by: null
  verified_at: null
dependency_gate:
  status: blocked
  verified_by: null
  verified_at: null
  evidence: []
branch:
  required: true
  name: null
  task_id: E3-T3
  one_task_only: true
  created_at: null
  pull_request: null
completion:
  completed_by: null
  completed_at: null
  pull_request: null
  evidence: []
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# E3-T3: Implement geocoder abstraction and cache

> Promoted after owner-approved spike revision 3. Status remains `draft` until implementation-plan revision 3 is owner-approved and remaining gates are satisfied. No code may start from this file yet.

## Outcome

Normalize extracted Warsaw locations and resolve them through a durable provider-neutral cache so only sufficiently precise, confident, in-scope, reviewed coordinates can become selected public pins.

## Original roadmap definition

- Priority/size: P0 / L
- Dependencies: E3-T1, E2-T2
- Work:
  - Normalize addresses and district names.
  - Add provider-neutral result mapping, persistent cache, Warsaw bounds, confidence/precision, and review states.
  - Add a no-network fixture/cached provider for the vertical proof.
  - Add the policy-controlled one-time Nominatim seed adapter.
  - Evaluate the verified Warsaw fixture against Geoapify and LocationIQ; use Geoapify first only if quality passes.
- Acceptance:
  - Repeated queries hit the database cache.
  - Out-of-bounds/low-precision results cannot become accepted pins automatically.
  - Provider rate, identification, timeout, retry, quota, attribution, secret, and fallback/defer policy is tested.
  - M1 resolves known fixtures with no external call.

## Scope

- Add versioned address/district/query/scope/result/review values plus inward-owned geocoder, cache, miss-ownership, and review ports.
- Add migrations for `geocode_results`, cross-process cache-miss claims/leases, the location's selected-result reference, and append-only review decisions.
- Make cache identity cover provider, normalizer version, scope version, request-shape version, and normalized query; persist bounded success/no-result/error/attribution/expiry semantics.
- Before any hosted call, atomically claim ownership of the identical miss across processes. The owner performs HTTP outside a database transaction; non-owners wait/recheck within a bound, and an expired owner may be replaced using owner/fencing semantics. Guarantee healthy concurrency and reconcile ambiguous retries after timeout/crash/lease takeover; do not promise an impossible at-most-once network call.
- Map provider-specific quality into common precision/confidence and validate Warsaw/Poland scope. Provider success never implies acceptance.
- Record selection and every automatic/manual review transition with geocode result ID, actor, reason code, prior/next state, review-policy version, and timestamp.
- Implement deterministic no-network fixtures, Geoapify, a LocationIQ comparator only under durable-storage-compatible terms, and the policy-locked one-time public Nominatim adapter.
- Run the owner-reviewed redacted Warsaw fixture through Geoapify and LocationIQ and record quality, terms, attribution, and selection evidence.

## Hard completion gate

The hosted comparison is mandatory E3-T3 acceptance evidence. Missing credentials or an owner-reviewed fixture may block starting the hosted acceptance run, but an unresolved blocker cannot replace the comparison, satisfy the task, or permit E3-T3 to be marked done.

## Acceptance criteria

- [ ] Normalization is deterministic/versioned across supported Polish/Russian/Ukrainian forms, preserves display/original values, and never invents an address.
- [ ] Repeated identical requests use the durable database cache without a provider call; any provider/normalizer/scope/request-version change creates a distinct identity.
- [ ] Two or more processes racing the same miss claim ownership under healthy concurrency, converge on one durable cache result after any ambiguous retry, avoid holding a database transaction during HTTP, and recover through bounded owner-failure takeover without requiring impossible at-most-once network semantics.
- [ ] Out-of-country/out-of-Warsaw, ambiguous, low-confidence, and district/city-precision results cannot become accepted exact pins automatically.
- [ ] Every accepted location references its selected `GeocodeResult`; selection/rejection/review changes retain append-only actor/reason/from/to/version/time lineage.
- [ ] Fixture/cached M1 cases resolve with no network and stable precision/confidence/review evidence.
- [ ] All adapters enforce tested key, identification, timeout, retry, rate, quota, attribution, storage, and defer policies without hidden provider fan-out.
- [ ] The reviewed hosted comparison records quality/terms evidence and selects Geoapify only if it passes; E3-T3 cannot complete without this evidence.
- [ ] Persisted/logged diagnostics contain no API keys, authorization headers, unapproved responses, contacts, or private source samples.

## Test plan

- Unit: normalization/versioning, query hash, result mapping, scope/review policy, selected-result transitions, review audit lineage, retry/rate/quota, and redaction.
- Integration: migration/head, cache hit/re-geocode, multiprocess identical-miss ownership, lease expiry/fencing takeover, ambiguous-retry reconciliation, selected-result constraints/atomicity, PostGIS point order/scope, and transaction failure.
- Contract: fake HTTP transports for each adapter, synthetic responses, attribution/terms metadata, and import-linter negative probes.
- Acceptance: explicit hosted Geoapify/LocationIQ comparison against the approved redacted fixture outside CI, with sanitized aggregate evidence committed.

## Dependencies and traceability

- Task dependencies: [E2-T2](../../E2-historical-export-parser-audit/tasks/E2-T2-implement-candidate-detection-and-typed-extractors.md), [E3-T1](E3-T1-create-schema-and-migrations.md), [E3-T2](E3-T2-implement-idempotent-persistence-and-reprocessing.md)
- Decision path: [ADR-021](../../../decisions/adr/ADR-021-use-cached-provider-neutral-geocoding.md) remains proposed and is referenced only as architecture research. [D-002](../../../decisions/deferred/D-002-recurring-geocoding-provider.md) remains deferred for recurring production provider selection and does not block implementing the provider-neutral abstraction, durable cache, fixtures, or adapters under an approved plan. Hosted comparison remains a hard completion gate; B-008 remains unresolved.
- Milestone: [M1](../../../milestones/M1-vertical-proof.md).
- Traceability: [Geocoding](../../../ingestion/GEOCODING.md), [Data model](../../../contracts/DATA_MODEL.md), [Security](../../../security/README.md).

## Approval and start boundary

- Spike gate is satisfied for revision 3. Implementation remains blocked until owner approval of implementation-plan revision 3 and remaining dependency/deferred gates required by the workflow.
- After authorization and completed dependencies, this task starts from then-current `main` on a dedicated E3-T3 branch and opens a PR targeting `main`.
- Production code, hosted calls, migrations, secrets/configuration changes, and disposable proof code remain out of scope while status is `draft` and the implementation gate is blocked.

## Affected modules and contracts

- See the approved/awaiting [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) revision 3 sequence entry for this task and [DATA_MODEL.md](../../../contracts/DATA_MODEL.md).

## Implementation notes

Material departures from the owner-approved plan revision invalidate the affected approval; editing this section alone does not authorize them.

## Rollout and rollback

Follow the task sequence entry in [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md): dedicated branch from then-current `main`, PR targeting `main`, forward-only migrations, schema-compatible rollback only, no destructive data recovery claims.

## Ready checklist

- [x] The file is authoritative under `tasks/`; no duplicate remains under `proposed-tasks/`.
- [x] Promotion source, promoter, and timestamp are recorded.
- [x] `spike_gate` references the owner-approved current spike revision 3 and is `satisfied`.
- [ ] `implementation_gate` references the owner-approved current implementation-plan revision containing this task ID/current revision, and is `satisfied`.
- [ ] Every dependency is `done` with `dependency_gate: satisfied`, or each incomplete dependency is a valid stacked ancestor; every deferred gate required for start is resolved per the approved plan.
- [ ] Scope and acceptance criteria match the approved plan.

## Start checklist

- [ ] Status passed through `ready`.
- [ ] One new branch contains this task ID.
- [ ] The branch and pull request contain this task only.
- [ ] `branch.name` and `branch.created_at` are recorded before setting `in_progress`.

## Done checklist

- [ ] Acceptance criteria pass.
- [ ] The global [definition of done](../../../workflow/DEFINITION_OF_DONE.md) passes.
- [ ] Completion actor, time, pull request, and evidence are recorded.
