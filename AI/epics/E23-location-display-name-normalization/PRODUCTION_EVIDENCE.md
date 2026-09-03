# E23 production evidence

Recorded 2026-09-02 after release `adcdb10` (deploy run
[33670234372](https://github.com/Flippylolz/WEF/actions/runs/33670234372)) on
`wef_hist_candidate`.

## Deploy

- Merged PRs [#316](https://github.com/Flippylolz/WEF/pull/316) (E23-T1 display-name
  normalization for new locations) and [#317](https://github.com/Flippylolz/WEF/pull/317)
  (E23-T2 backfill CLI).
- No new migration required; behavior is additive for new rows plus operator backfill
  for existing display fields.

## Location display-name backfill

Operator commands (see
[OPERATOR_COMMANDS.md](../../operations/OPERATOR_COMMANDS.md#wef-backfill-location-display-name)):

```bash
$COMPOSE exec -T api wef-backfill-location-display-name          # dry-run
$COMPOSE exec -T api wef-backfill-location-display-name --apply  # persist
$COMPOSE exec -T api wef-backfill-location-display-name          # idempotency check
```

| Step | `total` | `changed` | `unchanged` | `skipped_verified` | `failures` |
|------|---------|-----------|-------------|--------------------|------------|
| Dry-run | 1229 | 1110 | 113 | 968 | 6 |
| Apply | 1229 | 1110 | 113 | 968 | 6 |
| Re-run | 1229 | **0** | 1223 | 968 | 6 |

Database snapshot after apply:

| Metric | Count |
|--------|------:|
| Total locations | 2219 |
| Display names still containing Cyrillic | 588 |
| Locations with operator geocode lineage (skipped) | 975 |

The remaining Cyrillic names are expected for owner-verified locations (E18 curated
names are exempt), the six extraction failures, and locations without replayable
primary source evidence.

## Public API smoke

Default metro bbox sample (`GET /api/v1/map/locations?bbox=20.9,52.1,21.2,52.4`):

- First features now read Polish-forward, e.g.
  `ul. Dziekońskiego, Mokotów, Warszawa`, `ul. Giełdowa, Warszawa`.
- Cyrillic-template names still appear for verified/skipped locations in the same
  bbox (510 / 1835 features in a spot sample immediately after apply).

Public base URL: https://2fa54e2405.duckdns.org

## Follow-up review (non-blocking)

- **6 failures:** locations where archived primary source text did not replay a
  usable location line — route through E18 curation when needed.
- **3 fragment-only names** from the spike remain manual curation cases if still
  present after apply.
