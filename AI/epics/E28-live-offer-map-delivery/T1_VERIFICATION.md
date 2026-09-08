# E28-T1 verification

## Behavior and source comparison

`e2-v16` with `source-evidence-v3` recognizes current Russian apartment/house templates, separates total/parking/storage prices, and preserves inline room counts and specific semi-detached classification. The production comparison was read-only: the five authorized descriptions were read into memory, evaluated locally and discarded; no source export or private payload is committed.

On 8 September 2026 the modified parser detected all five audited posts (29714, 29724, 29734, 29742, 29752), extracted their evidenced totals, area and room count, and returned no warnings. The first and last posts were previously not candidates. The house's nearby locality remains unsupported until T3; parser `complete` must not be interpreted as map delivery. The three existing apartment offers also gain evidenced parking prices; the Aignera template gains the separately priced storage value.

The initial invented regression suite reproduced 13 failures on main before implementation; five negative cases already passed. After fixing the candidate, field, independent evidence, generic-house and room-summary issues, the focused suite passed 121 tests. It includes existing benchmark negatives and explicitly verifies that addon/rent/per-area amounts are not property totals, contradictory rooms/totals remain unapplied, and explicit detached/semi-detached evidence still conflicts.

A PostGIS integration regression ingests a simulated older parser miss, replays the same unchanged raw revision twice, and verifies exactly one offer/link/revision with correct minor units and preserved source checksum. It also verifies that parsing alone does not force visibility before geocoding.

## Validation

- `UV_PYTHON=3.13.2 make install`: frozen dependencies installed with pinned Python; Node 22.22.2 and pnpm 11.21.0 verified.
- `make lint`: passed Python/TypeScript lint and 17 architecture contracts.
- `make format-check`: passed.
- `make typecheck`: passed after correcting a test-only dynamic dataclass replacement.
- `make contract-check`: passed; no generated contract changes.
- Full `make test` uses isolated Compose project `wef-e28-test` and unique test image names. Its initial fresh-database startup raced the initialization server restart; the retry used the fully initialized disposable database. The backend then passed all 1,378 tests (91.23% combined coverage), including the new real replay/idempotency regression and critical coverage gates. The default frontend run had seven timing failures (six 5-second timeouts and one asynchronous-loading lookup). The same unchanged suite passed all 186 tests in 38 files with two workers, preserving every assertion and coverage gate: 96% lines, 90.07% branches; critical frontend coverage passed. This is a resource-bounded retry, not a clean result for the initial default `make test` invocation.

## Rollout boundary

No production data writes were performed during source verification. Normal release affects new ingestion and version-aware replay paths. No broad operator replay, AI calibration relaxation, forced visibility or provider quota change is part of T1. Existing location and gallery blockers remain assigned to T2–T5. T1 remains in progress until required current-head CI and release evidence are available; the epic remains open until end-to-end acceptance.

Exact test commands:

```sh
make test COMPOSE='docker compose --project-name wef-e28-test --file infra/compose.yaml --file /private/tmp/wef-e28-compose-test.yaml'
docker compose --project-name wef-e28-test --file infra/compose.yaml --file /private/tmp/wef-e28-compose-test.yaml --profile test run --rm --no-deps --volume /private/tmp/wef-e28/tmp/coverage/frontend:/coverage frontend-test pnpm test:coverage --coverage.reportsDirectory=/coverage/report --maxWorkers=2
python3 scripts/check_critical_coverage.py --frontend tmp/coverage/frontend/report/coverage-summary.json
```

The external temporary Compose override only assigns unique `wef-e28-backend:test` and `wef-e28-web:test` image names; it does not alter source, assertions, service behavior or thresholds. CI remains the default hosted required gate.
