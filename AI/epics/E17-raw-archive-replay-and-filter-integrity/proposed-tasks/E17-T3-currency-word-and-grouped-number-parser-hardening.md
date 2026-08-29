---
schema: ai-workflow/proposed-task@1
id: E17-T3
epic: E17
title: "Currency-word and grouped-number parser hardening"
status: proposed
revision: 1
actionable: false
priority: P1
size: S
milestone: M5
dependencies: []
requirement_ids: []
decision_ids:
  - ADR-006
deferred_decision_ids: []
source: ../../SPIKE.md#proposed-task-boundaries
promotion:
  status: not_promoted
  target: null
  promoted_by: null
  promoted_at: null
---

# E17-T3: Currency-word and grouped-number parser hardening

## Outcome

Amounts written with currency words instead of symbols parse with the correct
magnitude and currency: `💸Цена:850 000злотых` extracts as 850 000 PLN instead of the
current 850 with unknown currency.

## Scope

- Reviewed currency-word vocabulary mapping to ISO currencies, starting with PLN
  (`злотых`, `злотый`, `złotych`, `zlotych`); words are matched case-insensitively
  after NFKC normalization and may abut the number without whitespace.
- `_NUMBER`'s trailing boundary accepts an immediately following tracked currency
  word so the grouped form `850 000злотых` is not truncated to `850`.
- Per-area forms (`za m²`, `за м²`) keep working when a currency word is present.
- Sanitized fixture set built from real channel variants (symbol, ISO, word, mixed
  spacing, decimal comma) added to the extraction test corpus.
- Parser version bump per extraction conventions.

## Out of scope

- Non-PLN currency words (`евро`, `долларов`) unless fixtures prove need; adding them
  later is a vocabulary-only change.
- Any price display/frontend change — corrected values flow through existing
  contracts.

## Work

- Deterministic, span-tracked rules only; unknown currency words still emit
  `unknown_currency` rather than guessing PLN (fail-closed preserved).

## Acceptance criteria

- [ ] `850 000злотых`, `850 000 złotych`, `850000 злотых` all extract as
      `MoneyRange(850 000–850 000, PLN)` with exact source spans.
- [ ] Existing symbol/ISO price tests remain green; no regression in per-area or
      range parsing.
- [ ] An untracked currency word still yields null currency plus a warning.
- [ ] Full-export dry-run replay shows the aggregate price-extraction rate improve
      with no new warnings category explosion.

## Dependencies and gates

- None inside E17; independent of E17-T1/T2 and parallelizable.
- Benefits from E17-T2 for distributing the fix to already-ingested rows.

## Risks and notes

- Russian inflection variants (`злотого`, `злотыe` typo) — vocabulary must be a
  reviewed closed list, not a fuzzy matcher.

## Promotion checklist

- [ ] The epic spike is explicitly owner-approved for its current revision.
- [ ] Scope, acceptance, dependencies, priority, size, and traceability match the
      approved spike.
- [ ] Required deferred decisions are resolved.
- [ ] The file will be moved—not copied—to the epic's `tasks/`.
- [ ] Promotion metadata will identify the target, promoter, and timestamp.
