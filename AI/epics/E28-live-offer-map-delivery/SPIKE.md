---
schema: ai-workflow/spike@1
epic: E28
title: Why the newest channel offers fail to reach the map
status: approved
revision: 1
owner: owner
research_only: true
code_allowed: false
decision_ids: [ADR-006]
domain_docs: [AI/ingestion/PIPELINE.md, AI/operations/OPERATOR_COMMANDS.md]
proposed_task_ids: [E28-T1, E28-T2, E28-T3, E28-T4, E28-T5]
approval:
  required_role: owner
  status: approved
  decided_by: owner
  decided_at: "2026-09-08T06:48:39Z"
  approved_revision: 1
  evidence: OWNER_DIRECTION.md
invalidation:
  invalidated_by: null
  invalidated_at: null
  reason: null
  return_to: null
---

# Completed spike

## Question and method

Trace the latest five offer-bearing posts from Telegram through candidate detection, extraction, canonical offer, geocoding and media. Read existing code and production records in read-only transactions; inspect descriptions only after explicit owner authorization. No application code, disposable proof, provider requests or production writes were used for this spike. Observations are from 8 September 2026, approximately 06:17–06:48 UTC, deployed release `d70f445c48c4`.

## Verified evidence

- Transport is healthy/aligned at message 29761. All 90 recorded live runs in the preceding 48 hours succeeded. The preceding three days contain 48 messages, five with text, arriving within 15.83 seconds of publication. There is no evidence of a transport backlog.
- 29714 (Jerozolimskie apartment): no canonical offer. Current candidate rules miss the total-price label `Квартира:` and do not count Cyrillic square-metre units as area evidence. Its room/apartment signals do not reach the candidate threshold. The deterministic parser therefore never extracts otherwise available fields. The AI proposal remains `observed / creation_calibration_required`; the automatic creation validator accepts only a narrow colon-labeled family and does not cover this template.
- 29724 (Perkuna): one visible offer with an accepted building point. This is the positive control, not evidence that all new offers publish.
- 29734 (Aignera): canonical offer and completed media, but no point; validation terminal/unresolved. Provider evidence contains the matching Warsaw street and Mokotów district, yet reports `address_mismatch`. `source_address_evidence` recognizes Gocław specially but treats Sielce as another city. Municipal lookup cannot resolve the resulting source identity.
- 29742 (Szeligowska): canonical offer and completed current media, but no point; validation terminal/unresolved. Five provider street candidates agree on Warsaw/Bemowo/Szeligowska yet differ in representative coordinates; `choose_geocode_candidate` treats all different coordinates as material ambiguity. A street-only post needs verified street geometry/identity and honest street precision. Do not arbitrarily choose a high-confidence point or relax cross-street ambiguity.
- 29752 (Dosin house): no offer, `unclassified`, no recovery queue entry. The house-sale header, total-price label `Цена дома:`, Cyrillic area, and inline room count are unsupported or insufficient. The pin line has actual Dosin/Serock locality, not Warsaw. Existing extraction and scope hard-code Warsaw and the northern extent excludes this locality. Merely increasing detection will not place this offer on the map.
- The two missing offers' albums are recorded `unsupported / unassociated_source_evidence`. Discovery marks intentions done and uses insert-on-conflict-do-nothing, so later offer creation does not itself repair those associations. Source photo presence is not the problem.
- Aggregate media counts (28 completed, 22 unsupported, two quarantined) include revision/descriptor attempts. The two quarantines for 29742/29746 coexist with completed work for those source IDs. They must be reconciled against current revisions before claiming two images are missing.

Source descriptions and coordinates remain outside Git. Message IDs identify private operator acceptance cases; regression fixtures must replace names, amounts, sizes and copy while preserving the failing syntax.

## Existing seams

- `application/extraction.py`, `extraction_numbers.py`, `parse_quality.py`: candidate signals, separate money families, room extraction, independent recovery evidence and versions.
- `domain/geocoding.py`, `address_evidence.py`, `geocode_candidates.py`: normalization, city/district agreement, scope, precision and candidate review.
- `infrastructure/municipal_geocoder.py`, `location_validation_store.py`: authoritative geometry and versioned durable revalidation.
- `infrastructure/media_recovery_discovery.py`, `media_recovery_execution.py`: source association and verified media acquisition.
- Existing E24 recovery and E25 replay services own mutation paths; extend these seams without a second pipeline. E26 protected selections remain protected.

## Options and recommendation

1. Force all offers visible or accept the first provider point: rejected; creates wrong locations, missing galleries and false success.
2. Manual repairs for the five offers only: insufficient; the next identical post fails again and old media work stays terminal.
3. Repair evidenced template families, location identity/precision, and association convergence, then replay the bounded cohort and measure delivery: selected. Use deterministic extraction before paid AI. Keep automatic AI creation validation conservative until a separately tested family is calibrated.

The epic extends supported locality behavior to actual nearby locations present in the channel. It must not append Warsaw to non-Warsaw addresses. A locality-only post may receive a verified locality-level approximate pin with explicit precision; absent/ambiguous locality remains an actionable exception rather than invented coordinates. T3 owns the contract/scope/UI implications.

## Task boundaries and risks

T1 is a schema-free deterministic parser and evidence-policy fix. T2 repairs Warsaw identity and street geometry, with versioned revalidation. T3 owns nearby-locality extraction/resolution and honest coarse map display. T4 makes terminal unassociated media converge after canonical offer creation without crossing albums, using current-revision fencing. T5 verifies public map/gallery delivery and adds an outcome-based alert instead of interpreting transport health as success.

Uncertainty: municipal segmentation needs inspection under T2; current public gallery completeness needs reconciliation under T4/T5. Future source templates cannot be guaranteed by a five-post sample. Keep unclassified offer-like messages visible to delivery monitoring. Provider budgets/outages may delay publication; they must not silently terminalize recoverable work. Broad all-Poland expansion, new providers/dependencies, fabricated coordinates, and budget increases are outside revision 1.

## Exit evidence

Question answered; facts and remaining uncertainty separated; affected modules and operations identified; independently reviewable tasks and acceptance defined; research produced documentation only. Revision 1 advances under the owner's explicit research-then-fix direction, recorded in [OWNER_DIRECTION.md](OWNER_DIRECTION.md). Material scope/precision/privacy/budget changes return to the spike.
