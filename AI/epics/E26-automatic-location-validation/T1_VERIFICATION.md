# E26-T1 verification and limits

## Sanitized policy observation

The new tests compare fixed sanitized provider cases with the old policy's documented acceptance conditions (in-scope, building/street precision, confidence at least 0.80). These are synthetic coordinates, not suggested replacement locations.

| Case | Prior policy / adapter behavior | Current policy |
| --- | --- | --- |
| Jugosłowiańska query, Grochowska town hall, confidence 1.00 | Amenity mapped to building; source street never compared | `address_mismatch`, no point selected |
| Street-only Jugosłowiańska query, numbered building result | Building point could be accepted | `unsupported_precision`; bounded separately cached street request |
| Gocław before or after street text | Could display as replacement city | Source neighborhood retained, Warsaw and Praga-Południe context preserved |
| Two supported same-name candidates at different positions, unequal scores | First result used | Explicit ambiguity; higher confidence does not choose a point |
| Unsupported Ostrzycka query results | Confidence/scope could permit unrelated point | Durable two-form exhaustion, `no_match`, removed from pending work |
| Owner decision committed during provider I/O | Automatic selection could overwrite current state | Latest actor checked under location lock; owner/AI/unknown actor remains protected |
| AD-034 coarse pending acceptance | Worker copied points with manual_accept lineage | Worker no longer invokes blanket acceptance; explicit command uses current policy |

The original source and candidate cache evidence remain available; result IDs and append-only selection lineage are retained. No schema migration, identity rewrite, new dependency or provider-capacity change is required. Existing JSONB accepts the additive sanitized evidence envelope; legacy rows without it cannot prove address agreement.

## Validation

Locked dependencies installed with `UV_PYTHON=/Users/flippylolz/.asdf/installs/python/3.13.2/bin/python make install`; frontend uses the recorded Node 22.22.2 and pnpm 11.21.0. The initial sandbox cache denial was resolved by the approved dependency installation; the interpreter was explicitly corrected from system Python to the recorded version before tests.

- `UV_CACHE_DIR=/private/tmp/wef-e26-uv make lint`: pass, including all 17 architecture contracts and frontend lint.
- `UV_CACHE_DIR=/private/tmp/wef-e26-uv make typecheck`: pass, backend and frontend.
- `UV_CACHE_DIR=/private/tmp/wef-e26-uv make format-check`: pass.
- `UV_CACHE_DIR=/private/tmp/wef-e26-uv make contract-check`: pass; no OpenAPI/generated TypeScript drift.
- `COMPOSE_PROJECT_NAME=wef-e26-t1 make test`: final run passed 1,163 backend tests (90.38% combined line/branch coverage) and 169 frontend tests (95.76% lines, 90.14% branches). The three existing backend warnings did not fail the suite.
- `git diff --check`: pass.

Tests use an isolated Compose project and disposable PostGIS, not the shared live stack. No production provider calls or data changes were made for these tests.

## Remaining acceptance boundaries

This task changes future automatic selections. It does not verify the existing production Ostrzycka or Jugosłowiańska points as fixed. E26-T2 must record actual persisted revalidation outcomes; Ostrzycka additionally requires dated authoritative street geometry. E26-T3 and its E14-T5 dependency must prove real WebGL selection/precision/list behavior before broad existing-location application. Do not close the epic from these policy tests.

Rollback should stop automatic selection application while preserving evidence; reverting to AD-034 blanket acceptance would undo the safety fix. T2's queue/application controls and T3's honest discovery remain separately owned follow-ups.
