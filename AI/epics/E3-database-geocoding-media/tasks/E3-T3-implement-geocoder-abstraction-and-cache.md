---
schema: ai-workflow/task@1
id: E3-T3
epic: E3
title: "Implement geocoder abstraction and cache"
status: done
revision: 3
priority: P0
size: L
milestone: M1
dependencies: [E2-T2, E3-T1, E3-T2]
requirement_ids: [P-001, P-007]
decision_ids: [ADR-005, ADR-012, ADR-021]
deferred_decision_ids: []
promotion:
  source: ../proposed-tasks/E3-T3-implement-geocoder-abstraction-and-cache.md
  promoted_by: "Cursor Agent (owner-authorized after spike revision 3 approval)"
  promoted_at: "2026-08-14T00:42:00Z"
spike_gate:
  status: satisfied
  file: ../SPIKE.md
  approved_revision: 4
  verified_by: "Codex (owner-authorized gate reconciliation)"
  verified_at: "2026-08-15T09:31:46Z"
implementation_gate:
  status: satisfied
  file: ../IMPLEMENTATION_PLAN.md
  approved_revision: 4
  verified_by: "Codex (owner-authorized gate reconciliation)"
  verified_at: "2026-08-15T09:31:46Z"
dependency_gate:
  status: satisfied
  verified_by: "Codex (owner-authorized)"
  verified_at: "2026-08-15T06:29:24Z"
  evidence:
    - "E2-T2 | done | merged PR https://github.com/Flippylolz/WEF/pull/36"
    - "E3-T1 | done | merged PR https://github.com/Flippylolz/WEF/pull/11"
    - "E3-T2 | done | merged PR https://github.com/Flippylolz/WEF/pull/53 | squash 0016a7a"
branch:
  required: true
  name: feature/E3-T3-geocoder-cache
  task_id: E3-T3
  one_task_only: true
  created_at: "2026-08-15T06:29:24Z"
  pull_request: "https://github.com/Flippylolz/WEF/pull/59"
completion:
  completed_by: "Codex (owner-authorized gate reconciliation)"
  completed_at: "2026-08-15T09:31:46Z"
  pull_request: "https://github.com/Flippylolz/WEF/pull/59"
  evidence:
    - "Merged PR #59 implements the provider-neutral cache, miss ownership, review lineage, hosted adapters, and bounded Geoapify readiness proof"
    - "Owner-approved E3 spike/implementation-plan revision 4 removes the obsolete mandatory LocationIQ comparison and assigns private-input quality review to E3-T5"
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# E3-T3: Implement geocoder abstraction and cache

> Revision 3 reconciles the merged provider-neutral implementation and the owner's Geoapify-only historical decision in [PR #59](https://github.com/Flippylolz/WEF/pull/59). Owner-approved spike/plan revision 4 revalidated its gates and completion on 2026-08-15.

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
  - Prove bounded Geoapify credential/readiness behavior; complete-import sample quality and manual review belong to E3-T5.
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
- Implement deterministic no-network fixtures, Geoapify, a replaceable LocationIQ adapter that is inactive unless later selected under compatible terms, and the policy-locked one-time public Nominatim adapter.
- Prove Geoapify configuration, egress, neutral result mapping, attribution, and redacted failure behavior with one bounded readiness call. E3-T5 owns Geoapify-only quality/review evidence over private ignored historical inputs.

## Revised completion gate

PR #59 contains the owner's historical-provider decision and successful bounded Geoapify readiness evidence. No LocationIQ hosted comparison is required. Task completion still requires owner approval of revised E3 spike/plan revision 4 and gate revalidation; E3-T5 remains responsible for measured Geoapify quality and manual review before visible-pin acceptance.

## Acceptance criteria

- [x] Normalization is deterministic/versioned across supported Polish/Russian/Ukrainian forms, preserves display/original values, and never invents an address.
- [x] Repeated identical requests use the durable database cache without a provider call; any provider/normalizer/scope/request-version change creates a distinct identity.
- [x] Two or more processes racing the same miss claim ownership under healthy concurrency, converge on one durable cache result after any ambiguous retry, avoid holding a database transaction during HTTP, and recover through bounded owner-failure takeover without requiring impossible at-most-once network semantics.
- [x] Out-of-country/out-of-Warsaw, ambiguous, low-confidence, and district/city-precision results cannot become accepted exact pins automatically.
- [x] Every accepted location references its selected `GeocodeResult`; selection/rejection/review changes retain append-only actor/reason/from/to/version/time lineage.
- [x] Fixture/cached M1 cases resolve with no network and stable precision/confidence/review evidence.
- [x] All adapters enforce tested key, identification, timeout, retry, rate, quota, attribution, storage, and defer policies without hidden provider fan-out.
- [x] A bounded operator-only Geoapify readiness call proves configured egress, neutral mapping, attribution, and secret-safe failure behavior without committing provider payloads.
- [x] Persisted/logged diagnostics contain no API keys, authorization headers, unapproved responses, contacts, or private source samples.

## Test plan

- Unit: normalization/versioning, query hash, result mapping, scope/review policy, selected-result transitions, review audit lineage, retry/rate/quota, and redaction.
- Integration: migration/head, cache hit/re-geocode, multiprocess identical-miss ownership, lease expiry/fencing takeover, ambiguous-retry reconciliation, selected-result constraints/atomicity, PostGIS point order/scope, and transaction failure.
- Contract: fake HTTP transports for each adapter, synthetic responses, attribution/terms metadata, and import-linter negative probes.
- Acceptance: bounded operator-only Geoapify readiness outside CI, with only sanitized result-shape/status evidence; full private-input quality/review evidence is E3-T5 scope.

## Dependencies and traceability

- Task dependencies: [E2-T2](../../E2-historical-export-parser-audit/tasks/E2-T2-implement-candidate-detection-and-typed-extractors.md), [E3-T1](E3-T1-create-schema-and-migrations.md), [E3-T2](E3-T2-implement-idempotent-persistence-and-reprocessing.md)
- Decision path: [ADR-021](../../../decisions/adr/ADR-021-use-cached-provider-neutral-geocoding.md) selects Geoapify for the historical import through PR #59. [D-002](../../../decisions/deferred/D-002-recurring-geocoding-provider.md) remains deferred for recurring production selection and E8-T4 revalidation.
- Milestone: [M1](../../../milestones/M1-vertical-proof.md).
- Traceability: [Geocoding](../../../ingestion/GEOCODING.md), [Data model](../../../contracts/DATA_MODEL.md), [Security](../../../security/README.md).

## Approval and start boundary

- Historical implementation was completed and merged in PR #59 under spike/plan revision 3, but revision 2's hosted-comparison completion gate was not met.
- Revision 3 materially changes that acceptance boundary and remains invalidated until owner approval of spike/plan revision 4. No new implementation is authorized by this task revision.
- Production import and recurring geocoding remain outside E3-T3; E3-T5 and E8-T4/D-002 own those later gates.

## Affected modules and contracts

- See pending [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) revision 4 and [DATA_MODEL.md](../../../contracts/DATA_MODEL.md).

## Implementation notes

Material departures from the owner-approved plan revision invalidate the affected approval; editing this section alone does not authorize them.

## Rollout and rollback

Follow the task sequence entry in [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md): dedicated branch from then-current `main`, PR targeting `main`, forward-only migrations, schema-compatible rollback only, no destructive data recovery claims.

## Ready checklist

- [x] The file is authoritative under `tasks/`; no duplicate remains under `proposed-tasks/`.
- [x] Promotion source, promoter, and timestamp are recorded.
- [x] `spike_gate` references owner-approved current spike revision 4 and is `satisfied`.
- [x] `implementation_gate` references owner-approved current implementation-plan revision 4 containing E3-T3 revision 3 and is `satisfied`.
- [x] Every dependency is `done` with `dependency_gate: satisfied`, or each incomplete dependency is a valid stacked ancestor; every deferred gate required for start is resolved per the approved plan.
- [x] Scope and acceptance criteria match the approved plan.

## Start checklist

- [x] Status passed through `ready`.
- [x] One new branch contains this task ID.
- [x] The branch contains this task only; the pull request will be recorded after creation.
- [x] `branch.name` and `branch.created_at` are recorded before setting `in_progress`.

## Done checklist

- [x] Acceptance criteria pass with PR #59 evidence and revision-4 gate revalidation.
- [x] The global [definition of done](../../../workflow/DEFINITION_OF_DONE.md) passes.
- [x] Completion actor, time, pull request, and evidence are recorded.
