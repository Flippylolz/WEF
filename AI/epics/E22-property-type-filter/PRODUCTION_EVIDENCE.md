# E22 production evidence

Recorded 2026-09-02 after release `b28c9bc` (deploy run
[33659894308](https://github.com/Flippylolz/WEF/actions/runs/33659894308)) on
`wef_hist_candidate`.

## Deploy and migration

- Automatic production deploy from merged PR #302 (`f78bfb9`) and follow-up #304
  (`b28c9bc`, backfill dedupe fix).
- Migration `20260902_0019` applied during deploy (`wef-migrate` one-shot).

## Property-type backfill

Operator commands (see [OPERATOR_COMMANDS.md](../../operations/OPERATOR_COMMANDS.md#property-type-backfill-e22)):

```bash
$COMPOSE exec -T api wef-backfill-property-type          # dry-run
$COMPOSE exec -T api wef-backfill-property-type --apply  # persist
$COMPOSE exec -T api wef-backfill-property-type          # idempotency check
```

| Step | `total` | `changed` | Notes |
|------|---------|-----------|-------|
| Dry-run | 3319 | 2685 | Distinct offers with a primary source |
| Apply | 3319 | 2685 | Same counts persisted |
| Re-run | 3319 | **0** | Idempotent |

Classification buckets from final dry-run/apply: `apartment` 2663, `house` 21,
`semi_detached` 7, `unknown` 598, `conflicts` 31, `failures` 30.

Database totals after apply (`SELECT property_type, count(*) FROM offers GROUP BY 1`):

| property_type | count |
|---------------|-------|
| apartment | 2663 |
| unknown | 633 |
| house | 21 |
| semi_detached | 7 |

Offers without a primary source revision (3324 − 3319 = 5) remain at the migration
default `unknown`.

## Public API smoke

- `GET /api/v1/filter-facets` → `property_types: ["apartment", "house", "semi_detached"]`
- `GET /api/v1/map/locations?bbox=20.9,52.1,21.2,52.4` → 1835 features
- Same bbox with `property_type=apartment` → 1572 features

Public base URL: https://2fa54e2405.duckdns.org

## Follow-up review (non-blocking)

- **30 failures:** sample offers where listing extraction did not produce a candidate.
- **31 conflicts:** conflicting multilingual category phrases; stored as `unknown` by design.
