# E4-T4 map query performance evidence

Recorded on 2026-08-19 for the M1 synthetic seed against a local PostGIS database.

## Representative fixture

- Dataset: M1 catalog seed (`m1_fixture()`)
- Query: Warsaw bbox `20.7,52.0,21.4,52.4` with `rooms=(2,)` and `price_max=120_000_000`
- Environment: integration test database (`TEST_DATABASE_URL`)

## Result

- Warm-up: one query before measurement
- Sample size: 20 warmed iterations
- p95 latency target: `< 0.5 s` (500 ms)
- Assertion: `test_grouped_map_query_semantics_and_performance` in `apps/backend/tests/test_map_query_integration.py`

This evidence uses the synthetic MVP dataset only. A separate full-dataset tier remains gated on production import work (E3-T5 / E7-T6).
