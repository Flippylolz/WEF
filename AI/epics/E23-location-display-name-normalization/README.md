---
schema: ai-workflow/epic@1
id: E23
title: "Location display name normalization"
status: done
milestones: [M5]
owner: owner
spike: SPIKE.md
implementation_plan: IMPLEMENTATION_PLAN.md
---

# E23: Location display name normalization

## Outcome

Location names shown on the map, in the results list, and in offer details are
consistent, localized (Polish-forward), and free of raw source-post fragments.
Visitors see names like `ul. Wołoska, Służewiec, Mokotów, Warszawa` instead of
`ул. Dziekońskiego | Warszawa, Mokotów`, `Улица: Habicha 9`, or bullet lines
such as `• Трамвайная остановка - 2779 м`.

## User problem

The catalog currently writes each location's display name verbatim from the
source post's location line: `normalize_location_text` only collapses
whitespace. A production measurement on 2026-09-02 (2,055 locations in the
default metro view) found:

- **639 locations (31%)** carry Cyrillic-template names (`ул. …`, `Улица: …`,
  `Район …`).
- **3 locations** carry raw bullet/distance fragments as their entire name.
- **6 locations** sit just outside the Warsaw boundary (Pruszków ×4, Piaseczno
  area ×2). These are genuine neighboring-town offers, not geocoding errors.

A third of the catalog reading like an untranslated Telegram export undermines
trust in an otherwise curated product.

## User story

As a buyer browsing the map, I want every pin and result to show a clean,
consistent place name so that I can trust the catalog and compare locations
without parsing raw source text.

## Scope

- Canonical display-name rules for new locations: map Cyrillic labels
  (`ул.`, `Улица:`, `Район …`) to Polish-forward templates, strip markdown
  bullets/emoji/decoration, and prefer `street, district, Warszawa` ordering.
- A one-time backfill that renames **existing non-verified** locations from the
  retained raw evidence, keeping `normalized_address_hash` (identity) and
  E18 review state stable.
- Owner-verified locations keep their curated names.
- Parser replay coverage proving renames from the archived raw events.

## Non-goals

- No change to location identity (`normalized_address_hash`), geocoding
  coordinates, or review workflow.
- No bulk edits through generic admin forms (E18 console remains the
  curation path).
- Translating street names themselves; only label templates and decoration.
- Near-suburb badge/filter product work (deferred).

## Planning state

- [Spike revision 1](SPIKE.md) is owner-approved.
- [Implementation plan revision 1](IMPLEMENTATION_PLAN.md) is owner-approved.
- [Production evidence](PRODUCTION_EVIDENCE.md) recorded 2026-09-02 after deploy
  `adcdb10`.
- Tasks:
  - [E23-T1 — Add canonical location display-name normalization](tasks/E23-T1-display-name-normalization.md) (`done`, PR #316)
  - [E23-T2 — Backfill non-verified location display names](tasks/E23-T2-display-name-backfill.md) (`done`, PR #317)

## Dependencies

- E17 raw-archive replay (backfill provenance and rename mechanism).
- E18 owner location console (curation of residual fragment names).
