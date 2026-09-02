---
schema: ai-workflow/spike@1
epic: E23
title: "Location display name normalization research"
status: approved
revision: 1
owner: owner
research_only: true
code_allowed: false
decision_ids: []
domain_docs:
  - ../../ingestion/PIPELINE.md
  - ../../contracts/DATA_MODEL.md
  - ../../product/EXPERIENCE.md
  - ../E17-raw-archive-replay-and-filter-integrity/README.md
  - ../E18-owner-location-verification/README.md
proposed_task_ids:
  - E23-T1
  - E23-T2
approval:
  required_role: owner
  status: approved
  decided_by: "Flippylolz"
  decided_at: "2026-09-02T17:34:00Z"
  approved_revision: 1
  evidence: "Owner message in Cursor: '1 and 2' selecting E23 after the recommended Option 2 spike direction, with Polish-forward templates, verified-location backfill exemption, and near-suburb keep (E23-T3 deferred)."
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# Spike: Location display name normalization research

## Question

How should the catalog normalize location display names so that one third of
locations stop carrying raw Cyrillic source templates, without breaking
location identity, E18 owner verification, or the E17 raw-archive replay
lineage — and what happens to the handful of near-suburb and fragment-named
locations?

## Context and constraints

- `_resolve_location` (ingestion persistence adapter) names a new location via
  `normalize_location_text(parsed)`, which only collapses whitespace. The
  source post's location line language and decoration flow through verbatim.
- `display_name`/`display_address` are **write-once**: when
  `normalized_address_hash` already exists, `_resolve_location` returns the
  existing row without touching its names. E17 replay therefore does not
  rename existing locations.
- Location identity is `normalized_address_hash` (derived from the parsed
  location, independent of display text), so a rename backfill does not merge
  or split locations.
- E18 gives the owner a verified-location workflow; owner-curated names must
  survive any bulk normalization.
- P-007/P-002: source text shown publicly is the masked rendering; display
  names are separate fields and are already public.
- The catalog's contract is a Warsaw catalog; the map view bbox extends past
  the city boundary, so neighboring-town offers (Pruszków, Piaseczno) appear
  by design today.

## Evidence

Measured against production `GET /api/v1/map/locations` on 2026-09-02
(default metro bbox, 2,055 locations):

| Class | Count | Share | Examples |
|---|---|---|---|
| Cyrillic-template names (`ул. …`, `Улица: …`, `Район …`) | 639 | 31% | `ул. Dziekońskiego \| Warszawa, Mokotów`; `Улица: Habicha 9`; `Район Bemowo, ул. Powstańców Śląskich` |
| Raw bullet/distance fragments as the whole name | 3 | 0.1% | `• Трамвайная остановка - 2779 м`; `- 10 минут пешком до станции метро Służew,` |
| Near-suburb locations outside the city rect (20.85–21.27 E, 52.09–52.37 N) | 6 | 0.3% | `Pruszków, ul. Powstańców Śląskich`; `ул. Jasińskiego \| Piaseczno` |
| Bonus parser gap (found during post-deploy checks) | 1 offer | — | `floor_label` rendered `#3_комнаты` (room hashtag parsed as floor) |

Root cause of the Cyrillic class: the source channel writes location lines in
Russian-language templates; the parser anchors provenance to those lines but
never normalizes their labels.

## Options considered

1. **Status quo + E18 manual curation only.** No code, but 639 renames by hand
   is not realistic curation scope.
2. **Parser normalization + non-verified backfill (recommended).** Add
   display-name rules to the ingestion path: strip decoration, map Cyrillic
   labels to Polish equivalents (`ул.` → `ul.`, `Улица:` → drop, `Район X` →
   district), prefer `street, district, Warszawa` ordering, and backfill
   existing non-verified locations from retained raw evidence. Verified
   locations keep owner-curated names.
3. **Dual-language display.** Keep the original name and add a canonical alias
   in the UI. Doubles surface area for a cosmetic problem; rejected unless the
   owner wants to preserve source-language searchability.

## Recommendation

Option 2. Normalization lives beside the existing parser lineage (each rename
cites its raw evidence span), the backfill is a one-time bounded migration
excluding `review_status="verified"` locations, and the 3 fragment-named
locations route through the E18 console as curation cases.

## Binding owner decisions (revision 1)

1. **Canonical template:** Polish-forward Option 2 — map Cyrillic labels to
   Polish equivalents, strip bullets/emoji/decoration, prefer
   `street, district, Warszawa` ordering. Do not transliterate Polish street
   names that already appear in Latin script.
2. **Verified locations:** exempt from bulk backfill; E18 curated names remain.
3. **Near-suburb locations:** keep visible (status quo). Optional badge/filter
   work is deferred outside E23-T1/T2.

## Proposed task boundaries

- **E23-T1**: canonical display-name rules in the ingestion path (parser
  provenance preserved, unit tests over the measured name classes) — applies
  to new locations only.
- **E23-T2**: one-time backfill renaming non-verified existing locations from
  archived raw evidence, with before/after report and hash-stability guard;
  replay runbook entry.

## Risks and open questions

- Renames change rendered text that favorites (E10) and visit history store by
  location id, not name — no identity impact, but UI histories will show the
  new name retroactively (acceptable; note in the task).
- Normalization must not alter `normalized_address_hash`; a hash-changing bug
  would fork locations.
- Cyrillic street names themselves (e.g. `ул. Tuwima`) mix a Russian label with
  a Polish street name; the template maps but street tokens stay as written.
- Search/analytics that match on `display_name` text would see historical
  discontinuity.

## Invalidation triggers

- Owner rejects the canonical template direction.
- Discovery that archived raw events are insufficient to recompute names for
  the affected locations.

## Exit checklist

- [x] Root cause traced to `normalize_location_text` no-op and write-once
      naming in `_resolve_location`.
- [x] Production magnitudes measured (639 / 3 / 6).
- [x] Options and recommendation documented.
- [x] Owner approves the spike revision and the canonical template direction.

## Owner decision

Flippylolz approved spike revision 1 on 2026-09-02 via Cursor message `1 and 2`,
accepting Option 2 with the binding decisions above. Recorded in YAML
`approval`.
