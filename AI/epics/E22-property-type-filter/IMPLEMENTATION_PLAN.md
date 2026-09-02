---
schema: ai-workflow/implementation-plan@1
epic: E22
title: "Property type classification and filter delivery"
status: approved
revision: 2
owner: owner
spike_revision: 1
task_sequence:
  - id: E22-T1
    revision: 1
  - id: E22-T2
    revision: 1
  - id: E22-T3
    revision: 1
approval:
  required_role: owner
  status: approved
  decided_by: "Flippylolz"
  decided_at: "2026-09-02T15:58:32Z"
  approved_revision: 2
  evidence: "Owner statement in Codex task on 2026-09-02: 'I approve, create and set to automerge the doc PR.'"
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# Implementation Plan: Property type classification and filter delivery

## Approved spike baseline

[Spike revision 1](SPIKE.md) was explicitly approved by Flippylolz on
2026-09-02. It confirms the offer-level four-value stored taxonomy, three-value
filter input, evidence-only deterministic classification, unknown behavior,
historical replay, shared query semantics, and URL-backed multi-select UI. Its
premises remain current as of this revision.

Binding decisions remain ADR-005 for PostgreSQL persistence, ADR-006 for preserved
source/replay boundaries, ADR-012 for backend authority, and ADR-013 for committed
OpenAPI/generated clients. [P-010](../../product/EXPERIENCE.md#p-010-property-type-classification-and-filtering)
records the approved product behavior.

## Scope and outcome

Deliver one backend-owned, evidence-backed property-type dimension across source
ingestion, historical data, persistence, every catalog projection, generated
contracts, and the map explorer. The shipped selection offers Apartment, House,
and Semi-detached house; it is multi-select, URL-backed, additive to existing
filters, and safe for unknown historical values.

Explicit exclusions: taxonomy expansion; AI classification; location-level
classification; inferred values from non-text attributes; offer visibility or
availability changes; unrelated parser replay; production data mutation before
reviewed code and dry-run evidence are deployed.

## Ordered task sequence

### 1. E22-T1 — Add canonical property classification and safe backfill

- Task: [E22-T1 revision 1](tasks/E22-T1-property-classification-and-backfill.md).
- Dependency: completed E17-T2 replay infrastructure.
- Independent result: schema, classifier, persistence, and an idempotent operator
  backfill are reviewable without a public API or frontend change.
- Expected modules: catalog domain/model, ingestion extraction/domain/persistence,
  the next migration after the current head, replay/operator reporting,
  sanitized fixtures, data/ingestion/operations documentation.
- Verification: enum and conflict unit tests; migration upgrade/downgrade rehearsal;
  persistence/replay integration tests; changed/unchanged/failure report tests;
  assertions that visibility and unrelated fields are unchanged.
- Rollout: deploy the compatible column/classifier first; execute dry-run and
  review coverage; run bounded idempotent backfill only after review.
- Rollback: revert application image while the additive column remains; stop
  replay. A database downgrade is for local rehearsal only. Restoring earlier
  classifications requires the pre-run database recovery boundary, not code
  rollback.

### 2. E22-T2 — Extend catalog filter and public contracts

- Task: [E22-T2 revision 1](tasks/E22-T2-catalog-property-type-contracts.md).
- Dependencies: E22-T1 and completed E4-T4.
- Independent result: API consumers can query and render property type before the
  first-party UI changes.
- Expected modules: `MapFilters`, HTTP query model, shared SQL filter conditions,
  facet port/adapter/presenter, map/location/viewport query projections, offer
  detail, normalized ETag key, OpenAPI, generated TypeScript, contract documents.
- Verification: domain normalization; invalid-enum 422; OR-within/AND-across
  matrices; null/unknown behavior; map/list/location consistency; facets exclude
  `unknown`; response projection; OpenAPI drift; representative query plans.
- Rollout: additive `/v1` parameter/fields after the compatible migration exists.
  Old clients and URLs remain valid.
- Rollback: deploy the prior application; the unused additive column remains
  compatible. No data rollback is required.

### 3. E22-T3 — Add the URL-backed property type filter UI

- Task: [E22-T3 revision 1](tasks/E22-T3-property-type-filter-ui.md).
- Dependencies: E22-T2 and completed E13-T3.
- Independent result: the end-user filter and labels are isolated from persistence
  and query review.
- Expected modules: map search state/parser/serializer, API parameter mapping,
  filter controls, active chips/count/clear behavior, listing card, offer detail,
  English messages, unit/a11y/e2e fixtures.
- Verification: single/multiple selections; reload/share/back/forward; clear;
  facets loading/error with URL preservation; unknown label; keyboard and screen
  reader behavior; desktop/mobile mocked critical journey; production build.
- Rollout: deploy only after E22-T2 is live and representative classified facets
  exist. Smoke each choice and a multi-choice deep link.
- Rollback: deploy the prior web image; API and data remain additive and harmless.

## Cross-task architecture

- `PropertyType` is a catalog-domain value reused by ingestion. The backend owns
  classification and filter semantics; the frontend consumes generated types and
  renders labels only.
- The value is stored on `OfferRow`. `LocationRow` and `Development` remain
  unchanged because a grouped place can contain different property kinds.
- Deterministic extraction produces an `ExtractedValue[PropertyType]` with exact
  source spans. Persistence and replay use the existing offer/source transaction;
  the backfill does not parse or write in the frontend or query layer.
- `MapFilters.property_types` is the only public-query input and accepts the
  three-value filterable subset, not `unknown`. The map adapter's shared predicate
  is reused by map, selected-location, and viewport query paths.
- Facets are backend-derived from visible, accepted, in-scope rows and expose only
  filterable classified values. `unknown` remains a valid response value but is
  not a selectable facet in this version.
- OpenAPI remains the source for frontend API DTOs. No hand-written duplicate
  property enum is introduced in the web application.

## Data and migrations

- Add a non-null `offers.property_type` string column with a database constraint
  for `apartment`, `house`, `semi_detached`, and `unknown`; existing rows become
  `unknown` during the forward migration.
- Keep the migration compatible with the previous application release. The old
  application ignores the additive column; the new application reads/writes it.
- Update seed and test builders explicitly so fixtures state their intended type.
- Add property-type evidence to `OfferSource.extraction_json` and include the value
  in the canonical fingerprint for newly/replayed records without using the
  fingerprint as identity.
- Review representative production query plans. Add a partial/filter index only
  if measured evidence shows the existing indexes are insufficient.
- Backfill uses source-anchored replay, supports dry-run and bounded batches, and
  is idempotent. It emits aggregate redacted counts and a parser version, not raw
  descriptions.
- Application rollback does not undo classifications. A pre-operation database
  recovery point is the recovery boundary for a materially incorrect production
  backfill; persistent NUC data is not described as backed up while the repository's
  backup capability remains deferred.

## Security and privacy

- Classification runs inside the existing trusted ingestion boundary. No new
  source text is exposed publicly, logged, or sent to an external provider.
- Public requests accept a closed three-value input enum and bounded repeated
  values. `unknown` and other invalid values return the standard validation
  response and never become SQL fragments. Response DTOs use the four-value enum.
- Public responses continue to use explicit allowlists. The new field carries a
  coarse category only and reveals no contact, raw source, or internal provenance.
- Backfill reports contain IDs only where operationally necessary and otherwise
  aggregate counts; no raw message text or contacts are emitted.

## Test and verification strategy

- Unit: multilingual classifier precedence, punctuation/case variants, exact spans,
  generic-word rejection, multi-category conflict-to-unknown, normalized filter
  identity, URL parse/serialize, chip/count/reset behavior.
- Integration: migration, new/live persistence, replay idempotency, shared query
  matrices, facet visibility rules, selected-location match ranks, offer detail,
  and preservation of unrelated offer state.
- Contract: committed OpenAPI, generated TypeScript, public enum/parameter/field
  compatibility, contract documentation, no unexpected breaking change.
- Frontend: controls and results with loading/error/empty states; keyboard labels;
  responsive map panel; deep-link and navigation behavior.
- End to end: Apartment-only, House-only, Semi-detached-only, combined selection,
  clear, and shared URL journeys over synthetic sanitized fixtures.
- Operational: dry-run/backfill counts reconcile; a second run produces zero
  unintended changes; representative SQL plans meet the established catalog
  budget; production smoke verifies map/list/location agreement.
- Task branches run the repository-required `make lint`, `make test`,
  `make format-check`, `make typecheck`, and `make contract-check` where affected,
  plus Markdown links and diff whitespace checks.

## Operations, rollout, and rollback

1. Merge/deploy E22-T1 after green CI. The additive migration defaults legacy
   rows to `unknown`; new ingestion starts classifying supported evidence.
2. Run the property backfill in dry-run mode, review coverage/conflict/failure
   counts, and stop if guardrails fail. Run bounded apply and repeat dry-run to
   demonstrate idempotency.
3. Merge/deploy E22-T2. Smoke unfiltered requests, each property value, combined
   values, invalid input, facets, location offers, and viewport listings.
4. Merge/deploy E22-T3. Smoke desktop/mobile controls, deep links, clear, labels,
   and accessibility. Observe ordinary API/error telemetry without source values.

At every stage, the prior immutable application image is the code rollback. The
new column and classified values are forward-compatible. Disable/remove the web
control by rolling back E22-T3 if UI behavior fails; roll back E22-T2 if query
behavior fails; halt replay if classification quality fails. Do not destructively
clear production classifications without explicit owner authorization and a
reviewed recovery procedure.

## Risks and mitigations

- **Misclassification:** narrow evidence vocabulary, exact provenance, specific
  semi-detached precedence, conflict-to-unknown, sanitized multilingual fixtures,
  and reviewed dry-run metrics (E22-T1).
- **Poor usefulness due to unknown values:** publish coverage counts and expand
  classification only through a new approved revision; never trade correctness for
  guessed coverage (E22-T1).
- **Filter inconsistency:** one normalized object and shared SQL predicate with
  cross-projection tests (E22-T2).
- **Performance regression:** measured query-plan evidence and a justified index
  decision before rollout (E22-T2).
- **Contract/UI drift:** committed OpenAPI generation and facets-driven controls
  using generated types (E22-T2/T3).
- **Confusing labels:** explicitly define House vs Semi-detached house and show
  `bliźniak` context in product copy (E22-T3).

## Invalidation triggers

Return to the spike for taxonomy/semantics, ownership, inference source, external
AI/provider, or unknown-match changes. Return to this plan after spike approval for
material changes to sequence, promoted task revisions, modules, dependencies,
migrations, tests, rollout, or rollback.

## Approval checklist

- [x] The referenced spike revision has explicit owner approval and remains valid.
- [x] Every sequence entry is a promoted task with complete acceptance criteria
  and traceability.
- [x] Dependencies are complete, acyclic, and enforceable task by task.
- [x] Modules, contracts, tests, migrations, risks, rollout, and rollback
  are explicit for review.
- [x] Deferred decisions required for implementation are resolved.
- [x] No production or disposable proof code has been written.
- [x] `revision` represents the material plan being submitted.
- [x] `status` is `approved` and approval records revision 2.

## Owner decision

Flippylolz explicitly approved revision 2 in the Codex task on 2026-09-02. The
decision is recorded in the YAML `approval` object and authorizes this exact
sequence and scope, not blanket implementation: each task must still satisfy its
dependency gate and use its own dedicated feature branch and pull request.
