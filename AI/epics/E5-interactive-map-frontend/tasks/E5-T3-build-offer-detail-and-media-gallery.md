---
schema: ai-workflow/task@1
id: E5-T3
epic: E5
title: "Build offer detail and media gallery"
status: done
revision: 2
priority: P0
size: L
milestone: M3
dependencies: [E4-T3, E5-T1]
requirement_ids: [P-002, P-005, P-006, P-007]
decision_ids: [ADR-003, ADR-004, ADR-007, ADR-012]
deferred_decision_ids: []
promotion:
  source: ../proposed-tasks/E5-T3-build-offer-detail-and-media-gallery.md
  promoted_by: "Cursor Agent (owner-authorized)"
  promoted_at: "2026-08-13T19:30:00Z"
spike_gate:
  status: satisfied
  file: ../SPIKE.md
  approved_revision: 3
  verified_by: "Cursor Agent"
  verified_at: "2026-08-13T19:30:00Z"
implementation_gate:
  status: satisfied
  file: ../IMPLEMENTATION_PLAN.md
  approved_revision: 3
  verified_by: "Cursor Agent"
  verified_at: "2026-08-13T19:30:00Z"
dependency_gate:
  status: satisfied
  verified_by: "Cursor Agent (autonomous epic mission)"
  verified_at: "2026-08-19T18:40:00Z"
  evidence:
    - "E4-T3 | done | merged PR https://github.com/Flippylolz/WEF/pull/78"
    - "E5-T1 | done | merged on main before E5-T2"
branch:
  required: true
  name: feat/E5-T3-offer-detail-ui
  task_id: E5-T3
  one_task_only: true
  created_at: "2026-08-19T18:40:00Z"
  pull_request: "https://github.com/Flippylolz/WEF/pull/80"
completion:
  completed_by: "Cursor Agent (autonomous epic mission)"
  completed_at: "2026-08-19T18:47:00Z"
  pull_request: "https://github.com/Flippylolz/WEF/pull/80"
  evidence:
    - "Merged https://github.com/Flippylolz/WEF/pull/80 at d5c48f9 with green CI"
    - "make lint, typecheck, test passed locally before merge"
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# E5-T3: Build offer detail and media gallery

> E4-T3 is done (PR #78). E5-T1 and E5-T2 are done. Implementation is in progress on `feat/E5-T3-offer-detail-ui`.

## Outcome

Add a responsive, accessible offer-detail drawer/sheet that renders dated structured fields, server-masked source text, confidence and history, ordered public media, and a server-verified source action from the generated E4 detail contract.

## Scope

- Fetch full offer detail only after explicit offer selection; keep detail/media out of initial map and location-offer collection payloads.
- Render publication date, backend-owned display fields, typed apartment/parking/storage values, field confidence/caveats, location summary, and related source history without inferring availability.
- Render only the server-masked public source text.
- Add a responsive image/video gallery with optimized thumbnail-first loading, preserved aspect ratio, keyboard-operable next/previous/close controls, useful context-based alternative text, and native video controls.
- Show `Open in Telegram` only from a verified URL supplied by the backend; otherwise show safe source identity/date fallback without a dead link.
- Preserve matching/non-matching related-offer disclosure from the selected-location collection.
- Provide non-breaking placeholders for missing fields, media, files, and source links.

## Out of scope

- Frontend masking, confidence calculation, Telegram URL construction/verification, filter semantics, availability inference, media transformation/storage, uploads, authentication, contact reveal, analytics, or a frontend domain model.
- Responsive map/list restructuring and complete focus audit (E5-T4).
- Performance budgets, map lifecycle optimization, and production recovery pass (E5-T5).

## Affected modules and contracts

- Web catalog client and generated `GET /api/v1/offers/{offer_id}` types.
- Offer detail drawer/sheet, structured field presentation, media gallery, source action, translations, responsive styles, and focused tests.
- External dependency: [E4](../../E4-read-api-filter-contracts/README.md) task E4-T3 owns the public detail schema, masking, confidence, media URLs, verified link, and history semantics.

## Implementation notes

- Do not handwrite a substitute detail response. E4-T3's committed OpenAPI and regenerated frontend types are the only executable contract.
- Selection and gallery index are transient component state; detail server state belongs to TanStack Query and consumes its `AbortSignal`.
- A selected offer change cancels obsolete detail work and cannot display the previous offer under a new heading.
- Render unknown/missing values explicitly or omit them according to backend presentation fields; never turn absence into zero, false, unavailable, or inactive.
- External links use a new tab with `noopener noreferrer`.

## Acceptance criteria

- [x] Selecting an offer loads its generated-contract detail without adding full detail/media to the initial map or location-offer payload.
- [x] Publication date is prominent and no copy claims that an imported offer is currently available, active, or for sale now.
- [x] Typed fields, separate apartment/parking/storage values and included states, backend-owned confidence/caveats, masked public text, and source history render without client-side semantic recomputation.
- [x] Matching offers remain distinguished from additional non-matching related posts.
- [x] Images load thumbnail-first/full-on-demand with preserved aspect ratio, useful alternative text, keyboard next/previous/close, and deterministic missing-file placeholders.
- [x] Supported videos use native controls; unsupported or missing media does not break layout or keyboard flow.
- [x] `Open in Telegram` appears only for a backend-supplied verified HTTPS URL and uses safe external-link attributes; missing links show a useful non-link fallback.
- [x] Loading, empty, not-found, API error, and rapid offer-switch states remain accessible and do not expose raw responses, internal URLs, paths, contacts, or payloads.
- [x] Detail closes with focus restored to the invoking offer control and remains usable at 360 px and desktop widths.

## Test plan

- Unit: public field formatting/omission, media kind and placeholder selection, safe source-action capability, and no availability inference.
- Component: loading/success/not-found/error, rapid selection cancellation, fields/confidence/history, matching disclosure, missing values/media/link, gallery keyboard controls, native video, and focus restoration.
- Contract: generated E4 detail DTO only; no handwritten response interface or backend semantic duplication.
- End-to-end: list/pin → offer → detail → gallery/source action → close on seeded public data after E4-T3 provides a deterministic fixture.
- Security/accessibility/operations: safe-link attributes, masked-only text, leak assertions, labels/live status, keyboard flow, 360 px layout, production build, and runtime image.

## Rollout and rollback

Web-only additive behavior after E4-T3. Roll back the E5-T3 web commit/image to return to offer summaries; do not downgrade E4, delete media, or alter persisted data.

## Dependency blocker

- E5-T1 is done.
- E4-T3 is delivered by a parallel E4 agent. Keep this task `draft` with a blocked dependency gate until E4-T3 is `done`, or change the gate to `stacked` only after recording its branch, pull request URL, and exact ancestor head commit.
- A material difference between E4-T3's delivered contract and E5 spike/plan revision 3 invalidates this task rather than permitting a client adapter by guesswork.

## Ready checklist

- [x] This file is authoritative under `tasks/`; no duplicate remains under `proposed-tasks/`.
- [x] Promotion, spike revision 3, and implementation-plan revision 3 are recorded.
- [x] E4-T3 is complete or a valid direct ancestor PR is recorded; dependency gate is `satisfied` or `stacked`.
- [x] Status moves to `ready` only after every gate is valid.

## Start checklist

- [x] Status passed through `ready`.
- [x] Dedicated E5-T3 branch is created from the current E5-T2 branch after green parent CI and required E4 ancestry refresh.
- [x] Branch/PR contain E5-T3 only and metadata is recorded before `in_progress`.

## Done checklist

- [ ] Acceptance criteria pass.
- [ ] The global [definition of done](../../../workflow/DEFINITION_OF_DONE.md) passes.
- [ ] Dependency gate is `satisfied`; completion actor, time, pull request, and evidence are recorded.
